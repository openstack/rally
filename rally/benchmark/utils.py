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
import time

import fuel_health.cleanup as fuel_cleanup
from rally import utils


class Tester(object):

    def __init__(self, config_path):
        self._config_path = os.path.abspath(config_path)
        self._q = multiprocessing.Queue()

    def run_all(self, tests):
        res = []
        for test in tests:
            res.append(self.run(test))
        return res

    def run(self, test_args, times=1, concurrent=1):
        res = {}
        processes = {}
        proc_id = 0

        for i in xrange(min(concurrent, times)):
            proc_id = proc_id + 1
            processes.update(self._start_test_process(proc_id, test_args))

        while 1:
            for process in processes.keys():
                if not processes[process].is_alive():
                    del processes[process]
                    item = self._q.get()
                    res[item['proc_name']] = item
                    if proc_id < times:
                        proc_id = proc_id + 1
                        processes.update(self._start_test_process(proc_id,
                                                                  test_args))
            if not processes and proc_id >= times:
                break
            time.sleep(0.5)

        running = processes.keys()
        while 1:
            for process in running:
                if not processes[process].is_alive():
                    running.remove(process)
                    item = self._q.get()
                    res[item['proc_name']] = item
            if not running:
                break
            time.sleep(0.5)

        self._cleanup(self._config_path)
        return res

    def _start_test_process(self, id, test_args):
        proc_name = 'test_%d' % id
        args = (test_args, proc_name)
        test = multiprocessing.Process(name=proc_name, args=args,
                                       target=self._run_test)
        test.start()
        return {proc_name: test}

    def _run_test(self, test_args, proc_name):
        os.environ['OSTF_CONFIG'] = self._config_path
        with utils.StdOutCapture() as out:
            status = pytest.main(args=test_args)
            msg = filter(lambda line: line and '===' not in line,
                         out.getvalue().split('\n'))
            self._q.put({'msg': msg, 'status': status, 'proc_name': proc_name})

    def _cleanup(self, path):
        os.environ['OSTF_CONFIG'] = path
        fuel_cleanup.cleanup()
