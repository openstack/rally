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

import re
import unittest

from tests.functional import utils


TEST_ENV = {
    "OS_USERNAME": "admin",
    "OS_PASSWORD": "admin",
    "OS_TENANT_NAME": "admin",
    "OS_AUTH_URL": "http://fake/",
}


class DeploymentTestCase(unittest.TestCase):

    def test_create_fromenv_list_show(self):
        # NOTE(andreykurilin): `rally deployment create --fromenv` is
        #   hardcoded to OpenStack. Should be fixed as soon as the platforms
        #   will be introduced.
        rally = utils.Rally()
        rally.env.update(TEST_ENV)

        rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", rally("deployment list"))
        self.assertIn(TEST_ENV["OS_AUTH_URL"],
                      rally("deployment show"))

    def test_create_fromfile(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        rally("deployment create --name t_create_env --fromenv")
        with open("/tmp/.tmp.deployment", "w") as f:
            f.write(rally("deployment config"))
        rally("deployment create --name t_create_file "
              "--filename /tmp/.tmp.deployment")
        self.assertIn("t_create_file", rally("deployment list"))

    def test_create_empty(self):
        rally = utils.Rally()
        rally("deployment create --name t_empty")
        self.assertEqual("{}", rally("deployment config").strip())

    def test_destroy(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        rally("deployment create --name t_create_env --fromenv")
        self.assertIn("t_create_env", rally("deployment list"))
        rally("deployment destroy")
        self.assertNotIn("t_create_env", rally("deployment list"))

    def test_check_success(self):
        rally = utils.Rally()
        rally("deployment check")

    def test_check_fail(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        rally("deployment create --name t_create_env --fromenv")
        self.assertRaises(utils.RallyCliError, rally, "deployment check")

    def test_check_debug(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        rally("deployment create --name t_create_env --fromenv")
        config = rally("deployment config", getjson=True)
        config["openstack"]["admin"]["password"] = "fakepassword"
        file = utils.JsonTempFile(config)
        rally("deployment create --name t_create_file_debug "
              "--filename %s" % file.filename)
        self.assertIn("t_create_file_debug", rally("deployment list"))
        self.assertEqual(config, rally("deployment config", getjson=True))
        self.assertRaises(utils.RallyCliError, rally, "deployment check")

        try:
            rally("--debug deployment check")
        except utils.RallyCliError as e:
            self.assertIn(
                "[-] Unable to authenticate for user %(username)s in"
                " project %(tenant_name)s" %
                {"username": TEST_ENV["OS_USERNAME"],
                 "tenant_name": TEST_ENV["OS_TENANT_NAME"]},
                str(e))
            self.assertIn(
                "AuthenticationFailed: Failed to authenticate to %(auth_url)s"
                " for user '%(username)s' in project '%(tenant_name)s'" %
                {"auth_url": TEST_ENV["OS_AUTH_URL"],
                 "username": TEST_ENV["OS_USERNAME"],
                 "tenant_name": TEST_ENV["OS_TENANT_NAME"]},
                str(e))
        else:
            self.fail("rally deployment fails to raise error for wrong"
                      " authentication info")

    def test_use(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        output = rally(
            "deployment create --name t_create_env1 --fromenv")
        uuid = re.search(r"Using deployment: (?P<uuid>[0-9a-f\-]{36})",
                         output).group("uuid")
        rally("deployment create --name t_create_env2 --fromenv")
        rally("deployment use --deployment %s" % uuid)
        current_deployment = utils.get_global("RALLY_DEPLOYMENT",
                                              rally.env)
        self.assertEqual(uuid, current_deployment)

    # TODO(andreykurilin): Do not forget to move thes tests while splitting
    #   rally to main framework and openstack plugins

    def test_create_from_env_openstack_deployment(self):
        rally = utils.Rally()
        rally.env.update(TEST_ENV)
        rally("deployment create --name t_create_env --fromenv")
        config = rally("deployment config", getjson=True)
        self.assertIn("openstack", config)
        self.assertEqual(TEST_ENV["OS_USERNAME"],
                         config["openstack"]["admin"]["username"])
        self.assertEqual(TEST_ENV["OS_PASSWORD"],
                         config["openstack"]["admin"]["password"])
        if "project_name" in config["openstack"]["admin"]:
            # keystone v3
            self.assertEqual(TEST_ENV["OS_TENANT_NAME"],
                             config["openstack"]["admin"]["project_name"])
        else:
            # keystone v2
            self.assertEqual(TEST_ENV["OS_TENANT_NAME"],
                             config["openstack"]["admin"]["tenant_name"])
        self.assertEqual(TEST_ENV["OS_AUTH_URL"],
                         config["openstack"]["auth_url"])
