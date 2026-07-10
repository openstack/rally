# Copyright 2018: ITLook Inc.
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

import collections
import datetime as dt
import json
import tempfile
from unittest import mock
import uuid

from rally import exceptions
from rally.cli.commands import env
from rally.common import db
from rally.env import env_mgr
from tests.unit.cli import test


class EnvCommandsTestCase(test.CLITestCase):

    @staticmethod
    def gen_env_data(uid=None, name=None, description=None,
                     status=env_mgr.STATUS.INIT, spec=None, extras=None):
        return {
            "uuid": uid or str(uuid.uuid4()),
            "created_at": dt.datetime(2017, 1, 1),
            "updated_at": dt.datetime(2017, 1, 2),
            "name": name or str(uuid.uuid4()),
            "description": description or str(uuid.uuid4()),
            "status": status,
            "spec": spec or {},
            "extras": extras or {}
        }

    def _create_env(self, name="my-env", status=env_mgr.STATUS.READY):
        """Insert a real environment row and return its dict."""
        db.env_create(name=name, status=status, description="the env",
                      extras={}, config={}, spec={}, platforms=[])
        return db.env_get(name)

    @mock.patch("rally.cli.commands.env.print")
    def test__print(self, mock_print):
        env._print("Test42", silent=True)
        self.assertFalse(mock_print.called)
        env._print("Test42", silent=False)
        mock_print.assert_called_once_with("Test42")
        env._print("Test43")
        mock_print.assert_has_calls([mock.call("Test42"),
                                     mock.call("Test43")])

    def test_create_emtpy_use(self):
        result = self.invoke([
            "env", "create", "--name", "test_name",
            "--description", "test_description"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Using environment", result.output)
        self.assertIn("test_name", result.output)
        self.assertEqual("test_name", db.env_get("test_name")["name"])

    @mock.patch("rally.env.env_mgr.EnvManager.create")
    def test_create_spec_and_extra_no_use_to_json(self,
                                                  mock_env_manager_create):
        # env creation provisions platforms -- stub that one external step
        mock_env_manager_create.return_value.data = {"test": "test"}
        with tempfile.NamedTemporaryFile("w", suffix=".yml") as tf:
            tf.write("{\"a\": 1}")
            tf.flush()
            result = self.invoke([
                "env", "create", "--name", "n", "--description", "d",
                "--extras", "{\"extra\": 123}", "--spec", tf.name,
                "--json", "--no-use"])

        self.assertEqual(0, result.exit_code, result.output)
        mock_env_manager_create.assert_called_once_with(
            "n", {"a": 1}, description="d", extras={"extra": 123})
        self.assertIn(json.dumps({"test": "test"}, indent=2), result.output)

    def test_create_invalid_spec(self):
        # a spec that is not a dict is rejected by the real manager
        with tempfile.NamedTemporaryFile("w", suffix=".yml") as tf:
            tf.write("[]")
            tf.flush()
            result = self.invoke([
                "env", "create", "--name", "n", "--description", "d",
                "--spec", tf.name])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Env spec has wrong format:", result.output)

    @mock.patch("rally.env.env_mgr.EnvManager.create")
    @mock.patch("rally.env.env_mgr.EnvManager.create_spec_from_sys_environ")
    def test_create_from_sys_env(self, mock_create_spec_from_sys_environ,
                                 mock_env_manager_create):
        mock_create_spec_from_sys_environ.return_value = {
            "spec": {"foo": mock.Mock()},
            "discovery_details": collections.OrderedDict([
                ("foo", {"available": True, "message": "available"}),
                ("bar", {"available": False, "message": "not available",
                         "traceback": "trace"})
            ])
        }
        mock_env_manager_create.return_value.data = {
            **self.gen_env_data(), "platforms": {}}

        result = self.invoke([
            "env", "create", "--name", "n", "--description", "d",
            "--from-sysenv", "--no-use"])

        self.assertEqual(0, result.exit_code, result.output)
        for expected in (
            "includes specifications of 1 platform(s).",
            "Discovery information:",
            "\t - foo : available.",
            "\t - bar : not available.",
            "trace",
        ):
            self.assertIn(expected, result.output)
        mock_create_spec_from_sys_environ.assert_called_once_with()

    def test_create_with_incompatible_arguments(self):
        result = self.invoke([
            "env", "create", "--name", "n", "--description", "d",
            "--spec", "asd", "--from-sysenv"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("cannot be used together", result.output)

    @mock.patch("rally.env.env_mgr.EnvManager.create",
                side_effect=Exception("boom"))
    def test_create_exception(self, mock_env_manager_create):
        result = self.invoke([
            "env", "create", "--name", "n", "--description", "d"])

        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn("Something went wrong during env creation:",
                      result.output)

    @mock.patch("rally.env.env_mgr.EnvManager.cleanup")
    def test_cleanup(self, mock_env_manager_cleanup):
        env_ = self._create_env()
        mock_env_manager_cleanup.return_value = {
            "existing@docker": {
                "message": "Success", "discovered": 5, "deleted": 5,
                "failed": 0, "errors": []},
            "existing@openstack": {
                "message": "It is OpenStack. several failures are ok :)",
                "discovered": 10, "deleted": 8, "failed": 2,
                "errors": [{"message": "Port disappeared",
                            "traceback": "traceback"}]}
        }

        # a plain run prints a per-platform report and exits 1 on errors
        result = self.invoke(["env", "cleanup", env_["uuid"]])
        self.assertEqual(1, result.exit_code, result.output)
        for expected in (
                "Cleaning is finished. See the results bellow.",
                "Information for existing@docker platform.",
                "Status: Success", "Total discovered: 5", "Total deleted: 5",
                "Information for existing@openstack platform.",
                "Total failed: 2", "Errors:", "Port disappeared"):
            self.assertIn(expected, result.output)

        # --json dumps the raw result and still exits 1
        result = self.invoke(["env", "cleanup", env_["uuid"], "--json"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            json.dumps(mock_env_manager_cleanup.return_value, indent=2),
            result.output)

    @mock.patch("rally.env.env_mgr.EnvManager.destroy")
    def test_destroy(self, mock_env_manager_destroy):
        env_ = self._create_env()

        # a skipped destroy is reported as a failure and exits 1
        mock_env_manager_destroy.return_value = {
            "destroy_info": {"skipped": True, "message": "42"}}
        result = self.invoke(["env", "destroy", env_["uuid"]])
        self.assertEqual(1, result.exit_code, result.output)
        mock_env_manager_destroy.assert_called_once_with(False)
        self.assertIn("Failed to destroy env", result.output)

        # --skip-cleanup --json dumps the result and succeeds
        mock_env_manager_destroy.reset_mock()
        mock_env_manager_destroy.return_value = {
            "cleanup_info": {"skipped": False},
            "destroy_info": {"skipped": False, "message": "42"}}
        result = self.invoke([
            "env", "destroy", env_["uuid"], "--skip-cleanup", "--json"])
        self.assertEqual(0, result.exit_code, result.output)
        mock_env_manager_destroy.assert_called_once_with(True)
        self.assertIn(
            json.dumps(mock_env_manager_destroy.return_value, indent=2),
            result.output)

    def test_delete(self):
        # without --force the env must already be destroyed; --force deletes
        # the records regardless of state
        for force, status in ((False, env_mgr.STATUS.DESTROYED),
                              (True, env_mgr.STATUS.READY)):
            with self.subTest(force=force):
                env_ = self._create_env(name="env-%s" % force, status=status)
                args = ["env", "delete", env_["uuid"]]
                if force:
                    args.append("--force")

                result = self.invoke(args)
                self.assertEqual(0, result.exit_code, result.output)
                # the record is really gone
                self.assertRaises(exceptions.DBRecordNotFound,
                                  db.env_get, env_["uuid"])

    def test_list(self):
        # empty DB -> hint (table) or an empty JSON array
        result = self.invoke(["env", "list", "--json"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual("[]", result.output.strip())

        result = self.invoke(["env", "list"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(env.MSG_NO_ENVS, result.output)

        # populated -> the envs are listed
        env_a = self._create_env(name="env-a")
        env_b = self._create_env(name="env-b")
        result = self.invoke(["env", "list"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(env_a["uuid"], result.output)
        self.assertIn(env_b["uuid"], result.output)

    @mock.patch("rally.cli.commands.env.print")
    def test__show(self, mock_print):
        env_data = self.gen_env_data(
            uid="a77004a6-7fe5-4b75-a278-009c3c5f6b20",
            name="my best env",
            description="description")
        env_data["platforms"] = {}
        env._show(env_data, False, False)
        mock_print.assert_called_once_with(
            "+-------------+--------------------------------------+\n"
            "| uuid        | a77004a6-7fe5-4b75-a278-009c3c5f6b20 |\n"
            "| name        | my best env                          |\n"
            "| status      | INITIALIZING                         |\n"
            "| created_at  | 2017-01-01 00:00:00                  |\n"
            "| updated_at  | 2017-01-02 00:00:00                  |\n"
            "| description | description                          |\n"
            "| extras      | {}                                   |\n"
            "+-------------+--------------------------------------+")

    @mock.patch("rally.cli.commands.env.print")
    def test__show_to_json(self, mock_print):
        env._show("data", to_json=True, only_spec=False)
        mock_print.assert_called_once_with("\"data\"")

    @mock.patch("rally.cli.commands.env.print")
    def test__show_only_spec(self, mock_print):
        env._show({"spec": "data"}, to_json=False, only_spec=True)
        mock_print.assert_called_once_with("\"data\"")

    def test_show(self):
        env_ = self._create_env()

        # default table output
        result = self.invoke(["env", "show", env_["uuid"]])
        self.assertEqual(0, result.exit_code, result.output)
        for expected in (env_["uuid"], "my-env", "the env"):
            self.assertIn(expected, result.output)

        # --json dumps the whole record
        result = self.invoke(["env", "show", env_["uuid"], "--json"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual(env_["uuid"], json.loads(result.output)["uuid"])

        # --only-spec dumps just the spec
        result = self.invoke(["env", "show", env_["uuid"], "--only-spec"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertEqual({}, json.loads(result.output))

    @mock.patch("rally.env.env_mgr.EnvManager.get_info")
    def test_info(self, mock_env_manager_get_info):
        env_ = self._create_env()

        # --json dumps the info; a platform error makes it exit 1
        mock_env_manager_get_info.return_value = {"p1": {"info": {"a": True}}}
        result = self.invoke(["env", "info", env_["uuid"], "--json"])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn(
            json.dumps(mock_env_manager_get_info.return_value, indent=2),
            result.output)

        mock_env_manager_get_info.return_value = {
            "p1": {"info": {"a": False}},
            "p2": {"info": {}, "error": "some error"}}
        result = self.invoke(["env", "info", env_["uuid"], "--json"])
        self.assertEqual(1, result.exit_code, result.output)

        # table output renders one row per platform
        result = self.invoke(["env", "info", env_["uuid"]])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            "+----------+--------------+------------+\n"
            "| platform | info         | error      |\n"
            "+----------+--------------+------------+\n"
            "| p1       | {            |            |\n"
            "|          |   \"a\": false |            |\n"
            "|          | }            |            |\n"
            "| p2       | {}           | some error |\n"
            "+----------+--------------+------------+", result.output)

    @mock.patch("rally.env.env_mgr.EnvManager.check_health")
    def test_check(self, mock_env_manager_check_health):
        env_ = self._create_env()
        mock_env_manager_check_health.return_value = {
            "p1@p1": {"available": True, "message": "OK!"},
            "p2@p2": {"available": False, "message": "BAD !",
                      "traceback": "Filaneme\n  Codeline\nError"}}

        # default table
        result = self.invoke(["env", "check", env_["uuid"]])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            "+-----------+----------+---------+\n"
            "| Available | Platform | Message |\n"
            "+-----------+----------+---------+\n"
            "| :-)       | p1       | OK!     |\n"
            "| :-(       | p2       | BAD !   |\n"
            "+-----------+----------+---------+", result.output)

        # --detailed adds the Plugin column and the traceback
        result = self.invoke(["env", "check", env_["uuid"], "--detailed"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            "+-----------+----------+---------+--------+\n"
            "| Available | Platform | Message | Plugin |\n"
            "+-----------+----------+---------+--------+\n"
            "| :-)       | p1       | OK!     | p1@p1  |\n"
            "| :-(       | p2       | BAD !   | p2@p2  |\n"
            "+-----------+----------+---------+--------+", result.output)
        self.assertIn("Plugin p2@p2 raised exception:", result.output)
        self.assertIn("Filaneme\n  Codeline\nError", result.output)

        # --json dumps the raw health and exits 1 when unavailable
        result = self.invoke(["env", "check", env_["uuid"], "--json"])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            json.dumps(mock_env_manager_check_health.return_value, indent=2),
            result.output)

    def test_use(self):
        env_ = self._create_env()

        result = self.invoke(["env", "use", env_["uuid"]])
        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Using environment: %s" % env_["uuid"], result.output)

        # a non-existing env cannot be used
        missing = str(uuid.uuid4())
        result = self.invoke(["env", "use", missing])
        self.assertEqual(1, result.exit_code, result.output)
        self.assertIn(
            "Can't use non existing environment %s." % missing, result.output)

    @mock.patch("rally.cli.commands.env.envutils.update_globals_file")
    @mock.patch("rally.cli.commands.env.print")
    def test__use(self, mock_print, mock_update_globals_file):
        env._use("aa", True)
        self.assertFalse(mock_print.called)
        mock_update_globals_file.assert_called_once_with("RALLY_ENV", "aa")
        mock_update_globals_file.reset_mock()

        env._use("bb", False)
        mock_print.assert_called_once_with("Using environment: bb")
        mock_update_globals_file.assert_called_once_with("RALLY_ENV", "bb")
