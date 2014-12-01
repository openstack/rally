# Copyright 2014: Mirantis Inc.
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

import re
import unittest

import mock

from rally.cmd import envutils
from tests.functional import utils


class CliUtilsTestCase(unittest.TestCase):

    def setUp(self):
        super(CliUtilsTestCase, self).setUp()
        self.rally = utils.Rally()

    def _get_deployment_uuid(self, output):
        return re.search(
            r"Using deployment: (?P<uuid>[0-9a-f\-]{36})",
            output).group("uuid")

    def test_missing_argument(self):
        with self.assertRaises(utils.RallyCmdError) as e:
            self.rally("use task")
        self.assertIn("--uuid", e.exception.output)

    def test_deployment(self):
        with mock.patch.dict("os.environ", utils.TEST_ENV):
            output = self.rally(
                "deployment create --name t_create_env1 --fromenv")
            uuid = self._get_deployment_uuid(output)
            self.rally("deployment create --name t_create_env2 --fromenv")
            self.rally("use deployment --deployment %s" % uuid)
            current_deployment = envutils.get_global("RALLY_DEPLOYMENT")
            self.assertEqual(uuid, current_deployment)

    def test_task(self):
        cfg = {
            "Dummy.dummy_random_fail_in_atomic": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 100,
                        "concurrency": 5
                    }
                }
            ]
        }
        with mock.patch.dict("os.environ", utils.TEST_ENV):
            deployment_id = envutils.get_global("RALLY_DEPLOYMENT")
            config = utils.TaskConfig(cfg)
            output = self.rally(("task start --task %(task_file)s "
                                 "--deployment %(deployment_id)s") %
                                {"task_file": config.filename,
                                 "deployment_id": deployment_id})
            result = re.search(
                r"(?P<uuid>[0-9a-f\-]{36}) is started", output)
            uuid = result.group("uuid")
            self.rally("use task --uuid %s" % uuid)
            current_task = envutils.get_global("RALLY_TASK")
            self.assertEqual(uuid, current_task)
