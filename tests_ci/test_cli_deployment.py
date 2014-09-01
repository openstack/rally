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


import json
import unittest

import mock
import test_cli_utils as utils


class DeploymentTestCase(unittest.TestCase):

    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_create_fromenv_list_endpoint(self):
        with mock.patch.dict("os.environ", utils.TEST_ENV):
            self.rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", self.rally("deployment list"))
        self.assertIn(utils.TEST_ENV["OS_AUTH_URL"],
                      self.rally("deployment endpoint"))

    def test_create_fromfile(self):
        fake_d_conf = "/tmp/.tmp.deployment"
        self.rally("deployment create --name t_create_file --filename %s"
                   % fake_d_conf)
        self.assertIn("t_create_file", self.rally("deployment list"))

    def test_config(self):
        fake_d_conf = "/tmp/.tmp.deployment"
        self.rally("deployment create --name t_create_file --filename %s"
                   % fake_d_conf)
        with open(fake_d_conf, "r") as conf:
            self.assertDictEqual(json.loads(conf.read()),
                                 json.loads(self.rally("deployment config")))

    def test_destroy(self):
        with mock.patch.dict("os.environ", utils.TEST_ENV):
            self.rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", self.rally("deployment list"))
        self.rally("deployment destroy")
        self.assertNotIn("t_create_env", self.rally("deployment list"))

    def test_check_success(self):
        self.assertTrue(self.rally("deployment check"))

    def test_check_fail(self):
        with mock.patch.dict("os.environ", utils.TEST_ENV):
            self.rally("deployment create --name t_create_env --fromenv")
        self.assertRaises(utils.RallyCmdError, self.rally,
                          ("deployment check"))
