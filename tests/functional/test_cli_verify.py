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

import testtools

from tests.functional import utils


class VerifyTestCase(testtools.TestCase):

    def test_list_plugins(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify list-plugins")
        self.assertIn("fakeverifier", output)
        self.assertIn("installation", output)

    def test_create_list_show_verifier(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name fakeverify "
                       "--type installation --platform fakeverifier",
                       write_report=False)
        self.assertIn("fakeverify was installed successfully.",
                      output)

        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally("--debug verify list-verifiers", write_report=False)
        self.assertIn(uuid, output)
        self.assertIn("installed", output)

        output = rally("--debug verify show-verifier %s" % uuid,
                       write_report=False)
        self.assertIn(uuid, output)
        self.assertIn("installed", output)

    def test_list_tests(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name fakeverify "
                       "--type installation --platform fakeverifier",
                       write_report=False)
        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally("--debug verify list-verifier-tests"
                       " --id %s --pattern \\.test_testr\\." % uuid)
        self.assertIn(".test_testr.", output)

    def test_run_list_show_tests(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name fakeverify "
                       "--type installation --platform fakeverifier",
                       write_report=False)
        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally("verify start --id %s --tag tag-1 tag-2"
                       " --pattern \\.test_testr\\." % uuid)
        self.assertIn("successfully finished", output)

        verification_uuid = re.search(r"UUID=([0-9a-f\-]{36})",
                                      output).group(1)
        output = rally("verify list")
        self.assertIn(verification_uuid, output)

        output = rally("verify show %s" % verification_uuid)
        self.assertIn(".test_testr.", output)

    def test_delete_verification(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name fakeverify "
                       "--type installation --platform fakeverifier",
                       write_report=False)
        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally(
            "verify start --id %s --pattern \\.test_testr\\." % uuid)
        verification_uuid = re.search(r"UUID=([0-9a-f\-]{36})",
                                      output).group(1)
        output = rally("verify delete --uuid %s" % verification_uuid)
        self.assertIn("successfully deleted", output)
        output = rally("verify list")
        self.assertNotIn(verification_uuid, output)

    def test_rerun_verification(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name fakeverify "
                       "--type installation --platform fakeverifier",
                       write_report=False)
        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally(
            "verify start --id %s --pattern \\.test_testr\\." % uuid)
        verification_uuid = re.search(r"UUID=([0-9a-f\-]{36})",
                                      output).group(1)

        output = rally("verify rerun %s" % verification_uuid)
        self.assertIn("successfully finished", output)

    def test_add_list_delete_extension(self):
        rally = utils.Rally(plugin_path="tests/functional/extra")
        output = rally("verify create-verifier --name extension "
                       "--type extension --platform fakeverifier",
                       write_report=False)
        uuid = re.search(r"UUID=([0-9a-f\-]{36})", output).group(1)
        output = rally("--debug verify add-verifier-ext"
                       " --id %s --source fake_url" % uuid)
        self.assertIn(uuid, output)
        self.assertIn("successfully added", output)

        output = rally("--debug verify list-verifier-exts --id %s" % uuid)
        self.assertIn("fake_extension", output)
        self.assertIn("fake_entrypoint", output)

        output = rally("--debug verify delete-verifier-ext"
                       " --id %s --name fake_extension" % uuid)
        self.assertIn("uninstalled extension successfully.", output)
