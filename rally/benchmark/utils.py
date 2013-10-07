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

import multiprocessing
import os
import pytest
import traceback

import fuel_health.cleanup as fuel_cleanup

from rally.benchmark import base
from rally.benchmark import config
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import utils


LOG = logging.getLogger(__name__)


def _format_exc(exc):
    return [type(exc), str(exc), traceback.format_exc()]


def _run_scenario_loop(args):
    cls, endpoints, method_name, context, kwargs = args

    # NOTE(boris-42): Before each call of Scneraio we should init cls.
    #                 This is cause because this method is run by Pool.
    cls.class_init(endpoints)
    try:
        with utils.Timer() as timer:
            getattr(cls, method_name)(context, **kwargs)
    except Exception as e:
        return {"time": timer.duration(), "error": _format_exc(e)}
    return {"time": timer.duration(), "error": None}


class ScenarioRunner(object):
    """Tool that gets and runs one Scenario."""
    def __init__(self, task, cloud_config):
        self.task = task
        self.endpoints = cloud_config
        base.Scenario.register()

    def _run_scenario(self, ctx, cls, method, args, times, concurrent,
                      timeout):
        test_args = [(cls, self.endpoints, method, ctx, args)
                     for i in xrange(times)]

        pool = multiprocessing.Pool(concurrent)
        iter_result = pool.imap(_run_scenario_loop, test_args)

        results = []
        for i in range(len(test_args)):
            try:
                result = iter_result.next(timeout)
            except multiprocessing.TimeoutError as e:
                result = {"time": timeout, "error": _format_exc(e)}
            except Exception as e:
                result = {"time": None, "error": _format_exc(e)}
            results.append(result)
        return results

    def run(self, name, kwargs):
        cls_name, method_name = name.split(".")
        cls = base.Scenario.get_by_name(cls_name)

        args = kwargs.get('args', {})
        timeout = kwargs.get('timeout', 10000)
        times = kwargs.get('times', 1)
        concurrent = kwargs.get('concurrent', 1)

        cls.class_init(self.endpoints)
        ctx = cls.init(kwargs.get('init', {}))
        results = self._run_scenario(ctx, cls, method_name, args,
                                     times, concurrent, timeout)
        cls.cleanup(ctx)
        return results


def _run_test(args):
    test_args, ostf_config, proc_n = args
    os.environ['CUSTOM_FUEL_CONFIG'] = ostf_config

    with utils.StdOutCapture() as out:
        status = pytest.main(test_args)

    return {'msg': out.getvalue(),
            'status': status,
            'proc_name': proc_n}


def _run_cleanup(config):
    os.environ['CUSTOM_FUEL_CONFIG'] = config
    fuel_cleanup.cleanup()


class Verifier(object):

    def __init__(self, task, cloud_config_path, test_config_path=None):
        self._cloud_config_path = os.path.abspath(cloud_config_path)
        if test_config_path:
            self._test_config_manager = config.TestConfigManager(
                                                            test_config_path)
            os.environ['PYTEST_CONFIG'] = os.path.abspath(test_config_path)
        else:
            self._test_config_manager = None
        self.task = task
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

        task_uuid = self.task['uuid']
        res = []
        for test_name in tests:
            LOG.debug(_('Task %s: Launching benchmark `%s`...') %
                      (task_uuid, test_name))
            test_runs = tests_to_run.get(test_name, [{}])
            for i, test_run in enumerate(test_runs):
                times = test_run.get('times', 1)
                concurrent = test_run.get('concurrent', 1)
                os.environ['PYTEST_RUN_INDEX'] = str(i)
                res.append(self.run(tests[test_name],
                                    times=times, concurrent=concurrent))
            LOG.debug(_('Task %s: Completed benchmark `%s`.') %
                      (task_uuid, test_name))
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
        task_uuid = self.task['uuid']
        LOG.debug(_('Task %s: Running test: creating multiprocessing pool') %
                  task_uuid)
        iterable_test_args = ((test_args, self._cloud_config_path, n)
                              for n in xrange(times))
        pool = multiprocessing.Pool(concurrent)
        result_generator = pool.imap(_run_test, iterable_test_args)
        results = {}
        for result in result_generator:
            LOG.debug(_('Task %s: Process %s returned.') %
                      (task_uuid, result['proc_name']))
            results[result['proc_name']] = result
            if result['status'] and 'Timeout' in result['msg']:
                # cancel remaining tests if one test was timed out
                LOG.debug(_('Task %s: One of the tests timed out, '
                            'cancelling remaining tests...') % task_uuid)
                break
        LOG.debug(_('Task %s: Cleaning up...') % task_uuid)
        self._cleanup(self._cloud_config_path)
        LOG.debug(_('Task %s: Cleanup completed.') % task_uuid)
        return results

    def _cleanup(self, cloud_config_path):
        cleanup = multiprocessing.Process(target=_run_cleanup,
                                          args=(cloud_config_path,))
        cleanup.start()
        cleanup.join()
        return
