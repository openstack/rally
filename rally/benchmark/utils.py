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
from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging
from rally import utils


LOG = logging.getLogger(__name__)


def _format_exc(exc):
    return [str(type(exc)), str(exc), traceback.format_exc()]


def _run_scenario_loop(args):
    i, cls, endpoints, method_name, context, kwargs = args

    # NOTE(boris-42): Before each call of Scneraio we should init cls.
    #                 This is cause because this method is run by Pool.

    LOG.info("ITER: %s" % i)
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
        test_args = [(i, cls, self.endpoints, method, ctx, args)
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

        pool.close()
        pool.join()
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


def _run_test(test_args, ostf_config, queue):

    os.environ['CUSTOM_FUEL_CONFIG'] = ostf_config

    with utils.StdOutCapture() as out:
        status = pytest.main(test_args)

    queue.put({'msg': out.getvalue(), 'status': status,
               'proc_name': test_args[1]})


def _run_cleanup(config):

    os.environ['CUSTOM_FUEL_CONFIG'] = config
    fuel_cleanup.cleanup()


class Verifier(object):

    def __init__(self, task, cloud_config_path):
        self._cloud_config_path = os.path.abspath(cloud_config_path)
        self.task = task
        self._q = multiprocessing.Queue()

    @staticmethod
    def list_verification_tests():
        verification_tests_dict = {
            'sanity': ['--pyargs', 'fuel_health.tests.sanity'],
            'smoke': ['--pyargs', 'fuel_health.tests.smoke', '-k',
                      'not (test_007 or test_008 or test_009)'],
            'no_compute_sanity': ['--pyargs', 'fuel_health.tests.sanity',
                                  '-k', 'not infrastructure'],
            'no_compute_smoke': ['--pyargs', 'fuel_health.tests.smoke',
                                 '-k', 'user or flavor']
        }
        return verification_tests_dict

    def run_all(self, tests):
        """Launches all the given tests, trying to parameterize the tests
        using the test configuration.

        :param tests: Dictionary of form {'test_name': [test_args]}

        :returns: List of dicts, each dict containing the results of all
                  the run() method calls for the corresponding test
        """
        task_uuid = self.task['uuid']
        res = []
        for test_name in tests:
            res.append(self.run(tests[test_name]))
            LOG.debug(_('Task %s: Completed test `%s`.') %
                      (task_uuid, test_name))
        return res

    def run(self, test_args):
        """Launches a test (specified by pytest args).

        :param test_args: Arguments to be passed to pytest, e.g.
                          ['--pyargs', 'fuel_health.tests.sanity']

        :returns: Dict containing 'status', 'msg' and 'proc_name' fields
        """
        task_uuid = self.task['uuid']
        LOG.debug(_('Task %s: Running test: creating multiprocessing queue') %
                  task_uuid)

        test = multiprocessing.Process(target=_run_test,
                                       args=(test_args,
                                             self._cloud_config_path, self._q))
        test.start()
        test.join()
        result = self._q.get()
        if result['status'] and 'Timeout' in result['msg']:
            LOG.debug(_('Task %s: Test %s timed out.') %
                      (task_uuid, result['proc_name']))
        else:
            LOG.debug(_('Task %s: Process %s returned.') %
                      (task_uuid, result['proc_name']))
        LOG.debug(_('Task %s: Cleaning up...') % task_uuid)
        self._cleanup()
        LOG.debug(_('Task %s: Cleanup completed.') % task_uuid)
        return result

    def _cleanup(self):
        cleanup = multiprocessing.Process(target=_run_cleanup,
                                          args=(self._cloud_config_path,))
        cleanup.start()
        cleanup.join()
        return
