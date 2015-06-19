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
import re
import unittest

from tests.functional import utils


class DeploymentTestCase(unittest.TestCase):

    def setUp(self):
        super(DeploymentTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_create_fromenv_list_show(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", self.rally("deployment list"))
        self.assertIn(utils.TEST_ENV["OS_AUTH_URL"],
                      self.rally("deployment show"))

    def test_create_fromfile(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        with open("/tmp/.tmp.deployment", "w") as f:
            f.write(self.rally("deployment config"))
        self.rally("deployment create --name t_create_file "
                   "--filename /tmp/.tmp.deployment")
        self.assertIn("t_create_file", self.rally("deployment list"))

    def test_config(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        config = json.loads(self.rally("deployment config"))
        self.assertEqual(utils.TEST_ENV["OS_USERNAME"],
                         config["admin"]["username"])
        self.assertEqual(utils.TEST_ENV["OS_PASSWORD"],
                         config["admin"]["password"])
        self.assertEqual(utils.TEST_ENV["OS_TENANT_NAME"],
                         config["admin"]["tenant_name"])
        self.assertEqual(utils.TEST_ENV["OS_AUTH_URL"],
                         config["auth_url"])

    def test_destroy(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", self.rally("deployment list"))
        self.rally("deployment destroy")
        self.assertNotIn("t_create_env", self.rally("deployment list"))

    def test_check_success(self):
        self.assertTrue(self.rally("deployment check"))

    def test_check_fail(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        self.assertRaises(utils.RallyCliError, self.rally,
                          ("deployment check"))

    def test_recreate(self):
        self.rally.env.update(utils.TEST_ENV)
        self.rally("deployment create --name t_create_env --fromenv")
        self.rally("deployment recreate --deployment t_create_env")
        self.assertIn("t_create_env", self.rally("deployment list"))

    def test_use(self):
        self.rally.env.update(utils.TEST_ENV)
        output = self.rally(
            "deployment create --name t_create_env1 --fromenv")
        uuid = re.search(r"Using deployment: (?P<uuid>[0-9a-f\-]{36})",
                         output).group("uuid")
        self.rally("deployment create --name t_create_env2 --fromenv")
        self.rally("deployment use --deployment %s" % uuid)
        current_deployment = utils.get_global("RALLY_DEPLOYMENT",
                                              self.rally.env)
        self.assertEqual(uuid, current_deployment)
