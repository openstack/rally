# Copyright 2014: Mirantis Inc.
# Copyright 2014: Catalyst IT Ltd.
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

import os
import traceback
import unittest

from tests.functional import utils


class TestCertificationTask(unittest.TestCase):

    def test_task_samples_is_valid(self):
        rally = utils.Rally()
        full_path = os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir,
            "certification", "openstack")
        task_path = os.path.join(full_path, "task.yaml")
        args_path = os.path.join(full_path, "task_arguments.yaml")

        try:
            rally("task validate --task %s --task-args-file %s" % (task_path,
                                                                   args_path))
        except Exception:
            print(traceback.format_exc())
            self.assertTrue(False, "Wrong task config %s" % full_path)
