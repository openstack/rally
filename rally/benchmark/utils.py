# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools
import multiprocessing
import os
import pytest

import fuel_health.cleanup as fuel_cleanup

from rally.benchmark import config
from rally import utils


def parameterize_from_test_config(benchmark_name):
    """Decorator that configures the test function parameters through the
    test configuration stored in the temporary file (created by TestEngine).

    :param benchmark_name: The benchmark name. The test function settings
                           will be searched in the configuration under the key
                           `benchmark_name`.`function_name`
    """
    def decorator(test_function):
        @functools.wraps(test_function)
        def wrapper(*args, **kwargs):
            test_config = config.TestConfigManager()
            test_config.read(os.environ['PYTEST_CONFIG'])
            current_test_run_index = int(os.environ['PYTEST_RUN_INDEX'])
            tests_to_run = test_config.to_dict()['benchmark']['tests_to_run']
            current_test_runs = tests_to_run['%s.%s' % (benchmark_name,
                                             test_function.__name__)]
            current_test_config = current_test_runs[current_test_run_index]
            kwargs.update(current_test_config.get('args', {}))
            test_function(*args, **kwargs)
        return wrapper
    return decorator


def _run_test(args):
    test_args, ostf_config, proc_n = args
    os.environ['OSTF_CONFIG'] = ostf_config

    with utils.StdOutCapture() as out:
        status = pytest.main(test_args)

    return {'msg': out.getvalue(),
            'status': status,
            'proc_name': proc_n}


class Tester(object):

    def __init__(self, cloud_config_path, test_config_path=None):
        self._cloud_config_path = os.path.abspath(cloud_config_path)
        if test_config_path:
            self._test_config_manager = config.TestConfigManager(
                                                            test_config_path)
            os.environ['PYTEST_CONFIG'] = os.path.abspath(test_config_path)
        else:
            self._test_config_manager = None
        self._q = multiprocessing.Queue()

    def run_all(self, tests):
        """Launches all the given tests, trying to parameterize the tests
        using the test configuration.

        :param tests: Dictionary of form {'test_name': [test_args]}

        :returns: List of dicts, each dict containing the results of all
                  the run() method calls for the corresponding test
        """
        # NOTE(msdubov): Benchmark tests can be configured to be run several
        #                times and/or concurrently (using test configuration).
        if self._test_config_manager:
            test_config = self._test_config_manager.to_dict()
            tests_to_run = test_config['benchmark']['tests_to_run']
        else:
            tests_to_run = {}

        res = []
        for test_name in tests:
            test_runs = tests_to_run.get(test_name, [{}])
            for i, test_run in enumerate(test_runs):
                times = test_run.get('times', 1)
                concurrent = test_run.get('concurrent', 1)
                os.environ['PYTEST_RUN_INDEX'] = str(i)
                res.append(self.run(tests[test_name],
                                    times=times, concurrent=concurrent))
        return res

    def run(self, test_args, times=1, concurrent=1):
        """Launches a test (specified by pytest args) several times and/or
        concurrently (optional).

        :param test_args: Arguments to be passed to pytest, e.g.
                          ['--pyargs', 'fuel_health.tests.sanity']
        :param times: The number of times the test should be launched
        :param concurrent: The number of concurrent processed to be used while
                           launching the test

        :returns: Dict of dicts (each containing 'status', 'msg' and
                 'proc_name' fields', one dict for a single test run.
                  The keys in the top-level dictionary are the corresponding
                  process names
        """
        if '--timeout' not in test_args:
            timeout = str(60 * 60 * 60 / times)
            test_args.extend(['--timeout', timeout])

        iterable_test_args = ((test_args, self._cloud_config_path, n)
                              for n in xrange(times))
        pool = multiprocessing.Pool(concurrent)
        result_generator = pool.imap(_run_test, iterable_test_args)
        results = {}
        for result in result_generator:
            results[result['proc_name']] = result
            if result['status'] and 'Timeout' in result['msg']:
                # cancel remaining tests if one test was timed out
                break
        self._cleanup(self._cloud_config_path)
        return results

    def _cleanup(self, cloud_config_path):
        os.environ['OSTF_CONFIG'] = cloud_config_path
        fuel_cleanup.cleanup()
