# Copyright 2013: ITLook, Inc.
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
import os
import tempfile

import unittest

from tests.functional import utils


class EnvTestCase(unittest.TestCase):

    def test_create_no_spec(self):
        rally = utils.Rally()
        rally("env create --name empty --description de")
        self.assertIn("empty", rally("env list"))
        env_data = rally("env show --json", getjson=True)
        self.assertEqual("empty", env_data["name"])
        self.assertEqual("de", env_data["description"])
        self.assertEqual({}, env_data["extras"])
        self.assertEqual({}, env_data["platforms"])

    def _create_spec(self, spec):
        f = tempfile.NamedTemporaryFile(mode="w", delete=False)

        def unlink():
            os.unlink(f.name)

        self.addCleanup(unlink)

        f.write(json.dumps(spec, indent=2))
        f.close()
        return f.name

    def test_create_check_info_destroy_delete_with_spec(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")

        spec = self._create_spec({"good@fake": {}})
        rally("env create --name real --spec %s" % spec)
        env = rally("env show --json", getjson=True)
        self.assertIn("fake", env["platforms"])

        env_info = rally("env info --json", getjson=True)
        self.assertEqual({"good@fake": {"info": {"a": 1}}}, env_info)

        rally("env check --json")

    def test_list_empty(self):
        rally = utils.Rally()
        # TODO(boris-42): Clean this up somehow
        rally("env destroy MAIN")
        rally("env delete MAIN")
        self.assertEqual([], rally("env list --json", getjson=True))
        self.assertIn("There are no environments", rally("env list"))

    def test_list(self):
        rally = utils.Rally()
        envs = rally("env list --json", getjson=True)
        self.assertEqual(1, len(envs))
        self.assertEqual("MAIN", envs[0]["name"])
        self.assertIn("MAIN", rally("env list"))

    def test_use(self):

        def show_helper():
            return rally("env show --json", getjson=True)

        rally = utils.Rally()
        self.assertEqual("MAIN", show_helper()["name"])
        empty_uuid = rally("env create --name empty --json",
                           getjson=True)["uuid"]
        self.assertEqual("empty", show_helper()["name"])
        rally("env use MAIN")
        self.assertEqual("MAIN", show_helper()["name"])
        rally("env use %s" % empty_uuid)
        self.assertEqual("empty", show_helper()["name"])
        rally("env create --name empty2 --description de --no-use")
        self.assertEqual("empty", show_helper()["name"])
