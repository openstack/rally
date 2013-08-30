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

from rally import utils


class Tester(object):

    def __init__(self, config_path):
        self.config = os.path.abspath(config_path)
        self.q = multiprocessing.Queue()
        self.tests = {
            'sanity': ['--pyargs', 'fuel_health.tests.sanity'],
            'smoke': ['--pyargs', 'fuel_health.tests.smoke', '-k',
                      '"not (test_007 or test_008 or test_009)"'],
            'snapshot_test': ['--pyargs', 'fuel_health.tests.smoke', '-k',
                              '"test_snapshot"']
        }
        self.cleanUp = 'fuel_health.tests'

    def run(self, test_name, repeats=1):
        res = {}
        processes = {}
        for i in xrange(repeats):
            name = "test_{0}".format(i)
            args = (self.tests[test_name], self.config, self.q, name)
            processes[name] = multiprocessing.Process(name=name, args=args,
                                                      target=Tester._run_test)
            processes[name].start()
        running = processes.keys()
        while 1:
            for process in running:
                if not processes[process].is_alive():
                    running.remove(process)
                    item = self.q.get()
                    res[item['proc_name']] = item
            if not running:
                break
        return res

    @staticmethod
    def _run_test(test_name, path, queue, proc_name):
        os.environ['OSTF_CONFIG'] = path
        with utils.StdOutCapture() as out:
            status = pytest.main(args=test_name)
            msg = filter(lambda line: line and '===' not in line,
                         out.getvalue().split('\n'))
            queue.put({'msg': msg, 'status': status, 'proc_name': proc_name})
