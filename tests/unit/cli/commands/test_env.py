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
from unittest import mock
import uuid

from rally.cli.commands import env
from rally.env import env_mgr
from rally import exceptions
from tests.unit import test


class EnvCommandsTestCase(test.TestCase):

    def setUp(self):
        super(EnvCommandsTestCase, self).setUp()
        self.env = env.EnvCommands()
        # TODO(boris-42): api argument is not used by EvnCommands
        #                 it's going to be removed when we remove rally.api
        #                 from other commands
        self.api = None

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

    @mock.patch("rally.cli.commands.env.print")
    def test__print(self, mock_print):
        env._print("Test42", silent=True)
        self.assertFalse(mock_print.called)
        env._print("Test42", silent=False)
        mock_print.assert_called_once_with("Test42")
        env._print("Test43")
        mock_print.assert_has_calls([mock.call("Test42"), mock.call("Test43")])

    @mock.patch("rally.env.env_mgr.EnvManager.create")
    @mock.patch("rally.cli.commands.env.EnvCommands._show")
    def test_create_emtpy_use(self, mock_env_commands__show,
                              mock_env_manager_create):
        self.assertEqual(
            0, self.env.create(self.api, "test_name", "test_description"))
        mock_env_manager_create.assert_called_once_with(
            "test_name", {}, description="test_description", extras=None)
        mock_env_commands__show.assert_called_once_with(
            mock_env_manager_create.return_value.data,
            to_json=False, only_spec=False)

    @mock.patch("rally.env.env_mgr.EnvManager.create")
    @mock.patch("rally.cli.commands.env.open", create=True)
    @mock.patch("rally.cli.commands.env.print")
    def test_create_spec_and_extra_no_use_to_json(self, mock_print, mock_open,
                                                  mock_env_manager_create):
        mock_open.side_effect = mock.mock_open(read_data="{\"a\": 1}")
        mock_env_manager_create.return_value.data = {"test": "test"}
        self.assertEqual(
            0, self.env.create(self.api, "n", "d", extras="{\"extra\": 123}",
                               spec="spec.yml", to_json=True, do_use=False))

        mock_env_manager_create.assert_called_once_with(
            "n", {"a": 1}, description="d", extras={"extra": 123})
        mock_print.assert_called_once_with(
            json.dumps(mock_env_manager_create.return_value.data, indent=2))

    @mock.patch("rally.cli.commands.env.print")
    @mock.patch("rally.cli.commands.env.open", create=True)
    def test_create_invalid_spec(self, mock_open, mock_print):
        mock_open.side_effect = mock.mock_open(read_data="[]")
        self.assertEqual(
            1, self.env.create(self.api, "n", "d", spec="spec.yml"))
        mock_print.assert_has_calls([
            mock.call("Env spec has wrong format:"),
            mock.call("[]"),
            mock.call(mock.ANY)
        ])

    @mock.patch("rally.cli.commands.env.EnvCommands._show")
    @mock.patch("rally.env.env_mgr.EnvManager.create_spec_from_sys_environ")
    @mock.patch("rally.env.env_mgr.EnvManager.create")
    @mock.patch("rally.cli.commands.env.open", create=True)
    @mock.patch("rally.cli.commands.env.print")
    def test_create_from_sys_env(
            self, mock_print, mock_open, mock_env_manager_create,
            mock_env_manager_create_spec_from_sys_environ,
            mock_env_commands__show):
        result = {
            "spec": {"foo": mock.Mock()},
            "discovery_details": collections.OrderedDict([
                ("foo", {"available": True, "message": "available"}),
                ("bar", {"available": False, "message": "not available",
                         "traceback": "trace"})
            ])
        }
        mock_env_manager_create_spec_from_sys_environ.return_value = result

        self.assertEqual(
            0, self.env.create(self.api, "n", "d", spec=None,
                               from_sysenv=True, do_use=False))
        self.assertEqual(
            [
                # check that the number of listed platforms is right
                mock.call("Your system environment includes specifications of"
                          " 1 platform(s)."),
                mock.call("Discovery information:"),
                mock.call("\t - foo : available."),
                mock.call("\t - bar : not available."),
                mock.call("trace")
            ], mock_print.call_args_list)

        mock_env_manager_create_spec_from_sys_environ.assert_called_once_with()
        mock_env_manager_create.assert_called_once_with(
            "n", result["spec"], description="d", extras=None)
        self.assertFalse(mock_open.called)

    @mock.patch("rally.cli.commands.env.print")
    def test_create_with_incompatible_arguments(self, mock_print):
        self.assertEqual(
            1, self.env.create(self.api, "n", "d", spec="asd",
                               from_sysenv=True))

    @mock.patch("rally.env.env_mgr.EnvManager.create")
    @mock.patch("rally.cli.commands.env.print")
    def test_create_exception(self, mock_print, mock_env_manager_create):
        mock_env_manager_create.side_effect = Exception
        self.assertEqual(1, self.env.create(self.api, "n", "d"))
        mock_print.assert_has_calls([
            mock.call("Something went wrong during env creation:"),
            mock.call(mock.ANY)
        ])

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_cleanup(self, mock_print, mock_env_manager_get):
        env_ = mock.Mock()
        env_inst = mock_env_manager_get.return_value
        env_inst.cleanup.return_value = {
            "existing@docker": {
                "message": "Success",
                "discovered": 5,
                "deleted": 5,
                "failed": 0,
                "errors": []
            },
            "existing@openstack": {
                "message": "It is OpenStack. several failures are ok :)",
                "discovered": 10,
                "deleted": 8,
                "failed": 2,
                "errors": [
                    {"message": "Port disappeared",
                     "traceback": "traceback"}
                ]
            }
        }
        self.assertEqual(1, self.env.cleanup(self.api, env_))
        mock_env_manager_get.assert_called_once_with(env_)
        env_inst.cleanup.assert_called_once_with()

        actual_print = "\n".join(
            [call_args[0]
             for call_args, _call_kwargs in mock_print.call_args_list])
        expected_print = (
            "Cleaning up resources for %(env)s\n"
            "Cleaning is finished. See the results bellow.\n"
            "\n"
            "Information for existing@docker platform.\n"
            "%(hr)s\n"
            "Status: Success\n"
            "Total discovered: 5\n"
            "Total deleted: 5\n"
            "Total failed: 0\n"
            "\n"
            "Information for existing@openstack platform.\n"
            "%(hr)s\n"
            "Status: It is OpenStack. several failures are ok :)\n"
            "Total discovered: 10\n"
            "Total deleted: 8\n"
            "Total failed: 2\n"
            "Errors:\n"
            "\t- Port disappeared" % {"env": env_inst, "hr": "=" * 80})
        self.assertEqual(expected_print, actual_print)

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_cleanup_to_json(self, mock_print, mock_env_manager_get):
        env_ = mock.Mock()
        env_inst = mock_env_manager_get.return_value
        env_inst.cleanup.return_value = {
            "existing@docker": {
                "message": "Success",
                "discovered": 5,
                "deleted": 5,
                "failed": 0,
                "errors": []
            },
            "existing@openstack": {
                "message": "It is OpenStack. several failures are ok :)",
                "discovered": 10,
                "deleted": 8,
                "failed": 2,
                "errors": [
                    {"message": "Port disappeared",
                     "traceback": "traceback"}
                ]
            }
        }
        self.assertEqual(1, self.env.cleanup(self.api, env_, to_json=True))
        mock_print.assert_called_once_with(
            json.dumps(env_inst.cleanup.return_value, indent=2))

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_destroy(self, mock_print, mock_env_manager_get):
        env_ = mock.Mock()
        env_inst = mock_env_manager_get.return_value
        env_inst.destroy.return_value = {
            "destroy_info": {
                "skipped": True,
                "message": "42"
            }
        }
        self.assertEqual(1, self.env.destroy(self.api, env_))
        mock_env_manager_get.assert_called_once_with(env_)
        env_inst.destroy.assert_called_once_with(False)
        mock_print.assert_has_calls([
            mock.call("Destroying %s" % env_inst),
            mock.call(":-( Failed to destroy env %s: 42" % env_inst)
        ])

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_destroy_to_json(self, mock_print, mock_env_manager_get):
        env_ = mock.Mock()
        env_inst = mock_env_manager_get.return_value

        env_inst.destroy.return_value = {
            "cleanup_info": {
                "skipped": False
            },
            "destroy_info": {
                "skipped": False,
                "message": "42"
            }
        }
        self.assertEqual(
            0,
            self.env.destroy(self.api, env_, skip_cleanup=True, to_json=True))
        env_inst.destroy.assert_called_once_with(True)
        mock_print.assert_called_once_with(
            json.dumps(env_inst.destroy.return_value, indent=2))

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    def test_delete(self, mock_env_manager_get):
        env_ = mock.Mock()
        self.env.delete(self.api, env_)
        mock_env_manager_get.assert_called_once_with(env_)
        mock_env_manager_get.return_value.delete.assert_called_once_with(
            force=False)

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    def test_delete_force(self, mock_env_manager_get):
        env_ = mock.Mock()
        self.env.delete(self.api, env_, force=True)
        mock_env_manager_get.assert_called_once_with(env_)
        mock_env_manager_get.return_value.delete.assert_called_once_with(
            force=True)

    @mock.patch("rally.env.env_mgr.EnvManager.list")
    @mock.patch("rally.cli.commands.env.print")
    def test_list_empty(self, mock_print, mock_env_manager_list):
        mock_env_manager_list.return_value = []
        self.env.list(self.api, to_json=True)
        mock_print.assert_called_once_with("[]")
        mock_print.reset_mock()
        self.env.list(self.api, to_json=False)
        mock_print.assert_called_once_with(self.env.MSG_NO_ENVS)

    @mock.patch("rally.env.env_mgr.EnvManager.list")
    @mock.patch("rally.cli.commands.env.print")
    def test_list(self, mock_print, mock_env_manager_list):
        env_a = env_mgr.EnvManager(self.gen_env_data())
        env_b = env_mgr.EnvManager(self.gen_env_data())
        mock_env_manager_list.return_value = [env_a, env_b]

        self.env.list(self.api, to_json=True)
        mock_env_manager_list.assert_called_once_with()
        mock_print.assert_called_once_with(
            json.dumps([env_a.cached_data, env_b.cached_data], indent=2))

        for m in [mock_env_manager_list, mock_print]:
            m.reset_mock()

        self.env.list(self.api)
        mock_env_manager_list.assert_called_once_with()
        mock_print.assert_called_once_with(mock.ANY)

    @mock.patch("rally.cli.commands.env.print")
    def test__show(self, mock_print):
        env_data = self.gen_env_data(
            uid="a77004a6-7fe5-4b75-a278-009c3c5f6b20",
            name="my best env",
            description="description")
        env_data["platforms"] = {}
        self.env._show(env_data, False, False)
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
        self.env._show("data", to_json=True, only_spec=False)
        mock_print.assert_called_once_with("\"data\"")

    @mock.patch("rally.cli.commands.env.print")
    def test__show_only_spec(self, mock_print):
        self.env._show({"spec": "data"}, to_json=False, only_spec=True)
        mock_print.assert_called_once_with("\"data\"")

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.EnvCommands._show")
    def test_show(self, mock__show, mock_env_manager_get):
        env_ = mock.Mock()
        self.env.show(self.api, env_)
        mock_env_manager_get.assert_called_once_with(env_)
        mock__show.assert_called_once_with(
            mock_env_manager_get.return_value.data, to_json=False,
            only_spec=False)
        mock__show.reset_mock()
        self.env.show(self.api, env_, to_json=True)
        mock__show.assert_called_once_with(
            mock_env_manager_get.return_value.data, to_json=True,
            only_spec=False)

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_info_to_json(self, mock_print, mock_env_manager_get):
        mock_env_manager_get.return_value.get_info.return_value = {
            "p1": {"info": {"a": True}}}

        self.assertEqual(0, self.env.info(self.api, "any", to_json=True))
        mock_env_manager_get.assert_called_once_with("any")
        mock_print.assert_called_once_with(
            json.dumps(mock_env_manager_get.return_value.get_info.return_value,
                       indent=2)
        )
        mock_env_manager_get.return_value.get_info.return_value = {
            "p1": {"info": {"a": False}},
            "p2": {"info": {}, "error": "some error"}
        }
        self.assertEqual(1, self.env.info(self.api, "any", to_json=True))

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_info(self, mock_print, mock_env_manager_get):
        mock_env_manager_get.return_value.get_info.return_value = {
            "p1@pl1": {"info": {"a": False}},
            "p2@pl2": {"info": {}, "error": "some error"}
        }
        self.assertEqual(1, self.env.info(self.api, "any"))
        mock_print.assert_has_calls([
            mock.call(mock_env_manager_get.return_value),
            mock.call(
                "+----------+--------------+------------+\n"
                "| platform | info         | error      |\n"
                "+----------+--------------+------------+\n"
                "| p1@pl1   | {            |            |\n"
                "|          |   \"a\": false |            |\n"
                "|          | }            |            |\n"
                "| p2@pl2   | {}           | some error |\n"
                "+----------+--------------+------------+"
            )
        ])

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_check(self, mock_print, mock_env_manager_get):
        mock_env_manager_get.return_value.check_health.return_value = {
            "p1@p1": {"available": True, "message": "OK!"},
            "p2@p2": {"available": False, "message": "BAD !"}
        }
        self.assertEqual(1, self.env.check(self.api, "env_42"))
        mock_env_manager_get.assert_called_once_with("env_42")

        mock_print.assert_has_calls([
            mock.call("%s :-(" % mock_env_manager_get.return_value),
            mock.call(
                "+-----------+----------+---------+\n"
                "| Available | Platform | Message |\n"
                "+-----------+----------+---------+\n"
                "| :-)       | p1       | OK!     |\n"
                "| :-(       | p2       | BAD !   |\n"
                "+-----------+----------+---------+"
            )
        ])

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_check_detailed(self, mock_print, mock_env_manager_get):
        mock_env_manager_get.return_value.check_health.return_value = {
            "p1@p1": {"available": True, "message": "OK!"},
            "p2@p2": {"available": False, "message": "BAD !",
                      "traceback": "Filaneme\n  Codeline\nError"}
        }
        self.assertEqual(1, self.env.check(self.api, "env_42", detailed=True))
        mock_env_manager_get.assert_called_once_with("env_42")

        print(mock_print.call_args_list)
        mock_print.assert_has_calls([
            mock.call("%s :-(" % mock_env_manager_get.return_value),
            mock.call(
                "+-----------+----------+---------+--------+\n"
                "| Available | Platform | Message | Plugin |\n"
                "+-----------+----------+---------+--------+\n"
                "| :-)       | p1       | OK!     | p1@p1  |\n"
                "| :-(       | p2       | BAD !   | p2@p2  |\n"
                "+-----------+----------+---------+--------+"
            ),
            mock.call("----"),
            mock.call("Plugin p2@p2 raised exception:"),
            mock.call("Filaneme\n  Codeline\nError")
        ])

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.print")
    def test_check_to_json(self, mock_print, mock_env_manager_get):
        mock_env_manager_get.return_value.check_health.return_value = {
            "p1": {"available": True}}

        self.assertEqual(0, self.env.check(self.api, "some_env", to_json=True))
        mock_env_manager_get.assert_called_once_with("some_env")
        mock_print.assert_called_once_with(
            json.dumps(
                mock_env_manager_get.return_value.check_health.return_value,
                indent=2)
        )

        mock_env_manager_get.return_value.check_health.return_value = {
            "p1": {"available": False}}
        self.assertEqual(1, self.env.check(self.api, "some_env", to_json=True))

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env._print")
    def test_use_not_found(self, mock__print, mock_env_manager_get):
        mock_env_manager_get.side_effect = exceptions.DBRecordNotFound(
            criteria="", table="")
        env_ = str(uuid.uuid4())
        self.assertEqual(1, self.env.use(self.api, env_))
        mock_env_manager_get.assert_called_once_with(env_)
        mock__print.assert_called_once_with(
            "Can't use non existing environment %s." % env_, False)

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    @mock.patch("rally.cli.commands.env.EnvCommands._use")
    def test_use(self, mock__use, mock_env_manager_get):
        mock_env_manager_get.side_effect = [
            mock.Mock(uuid="aa"), mock.Mock(uuid="bb")
        ]
        self.assertIsNone(self.env.use(self.api, "aa"))
        self.assertIsNone(self.env.use(self.api, "bb", to_json=True))

        mock_env_manager_get.assert_has_calls(
            [mock.call("aa"), mock.call("bb")])
        mock__use.assert_has_calls(
            [mock.call("aa", False), mock.call("bb", True)])

    @mock.patch("rally.cli.commands.env.envutils.update_globals_file")
    @mock.patch("rally.cli.commands.env.print")
    def test__use(self, mock_print, mock_update_globals_file):
        self.env._use("aa", True)
        self.assertFalse(mock_print.called)
        mock_update_globals_file.assert_called_once_with("RALLY_ENV", "aa")
        mock_update_globals_file.reset_mock()

        self.env._use("bb", False)
        mock_print.assert_called_once_with("Using environment: bb")
        mock_update_globals_file.assert_called_once_with("RALLY_ENV", "bb")
