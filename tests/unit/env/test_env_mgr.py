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

import mock

from rally.env import env_mgr
from rally.env import platform
from rally import exceptions
from tests.unit import test


class EnvManagerTestCase(test.TestCase):

    def test_init(self):
        data = {"uuid": "any", "balbalba": "balbal"}
        mgr = env_mgr.EnvManager(data)
        self.assertEqual("any", mgr.uuid)
        self.assertEqual(data, mgr._env)

    @mock.patch("rally.common.db.env_get_status")
    def test_status_property(self, mock_env_get_status):
        self.assertEqual(mock_env_get_status.return_value,
                         env_mgr.EnvManager({"uuid": "any"}).status)

        mock_env_get_status.assert_called_once_with("any")

    @mock.patch("rally.common.db.platforms_list")
    @mock.patch("rally.common.db.env_get")
    def test_data_property(self, mock_env_get, mock_platforms_list):
        mock_platforms_list.return_value = [42, 43, 44]
        mock_env_get.return_value = {
            "id": "66",
            "uuid": "666",
            "created_at": mock.Mock(),
            "updated_at": mock.Mock(),
            "name": "42",
            "description": "Some description",
            "status": "some status",
            "spec": "some_spec",
            "extras": "some_extras",
        }

        result = env_mgr.EnvManager({"uuid": 111}).data
        for field in ["name", "description", "status", "spec", "extras",
                      "created_at", "updated_at", "uuid", "id"]:
            self.assertEqual(mock_env_get.return_value[field], result[field])
        self.assertEqual(mock_platforms_list.return_value, result["platforms"])

        mock_platforms_list.assert_called_once_with(111)
        mock_env_get.assert_called_once_with(111)

    @mock.patch("rally.common.db.platforms_list")
    def test__get_platforms(self, mock_platforms_list):

        @platform.configure(name="some", platform="foo")
        class FooPlatform(platform.Platform):
            pass

        mock_platforms_list.side_effect = [
            [],
            [
                {
                    "uuid": "1",
                    "plugin_name": "some@foo",
                    "plugin_data": "plugin_data",
                    "plugin_spec": "plugin_data",
                    "platform_data": "platform_data",
                    "status": "INIT"
                },
                {
                    "uuid": "2",
                    "plugin_name": "some@foo",
                    "plugin_data": None,
                    "plugin_spec": "plugin_data",
                    "platform_data": None,
                    "status": "CREATED"
                },
            ]
        ]

        self.assertEqual([], env_mgr.EnvManager({"uuid": 42})._get_platforms())
        mock_platforms_list.assert_called_once_with(42)

        result = env_mgr.EnvManager({"uuid": 43})._get_platforms()
        self.assertEqual(2, len(result))

        for i, r in enumerate(sorted(result, key=lambda x: x.uuid)):
            self.assertIsInstance(r, FooPlatform)
            self.assertEqual("some@foo", r.get_fullname())
            self.assertEqual(str(i + 1), r.uuid)

        mock_platforms_list.assert_has_calls([mock.call(42), mock.call(43)])

    @mock.patch("rally.common.db.env_get",
                return_value={"uuid": "1"})
    def test_get(self, mock_env_get):
        self.assertEqual("1", env_mgr.EnvManager.get("1").uuid)
        mock_env_get.assert_called_once_with("1")

    @mock.patch("rally.common.db.env_list",
                return_value=[{"uuid": "1"}, {"uuid": "2"}])
    def test_list(self, mock_env_list):
        result = env_mgr.EnvManager.list()

        for r in result:
            self.assertIsInstance(r, env_mgr.EnvManager)

        self.assertEqual(set(r.uuid for r in result), set(["1", "2"]))
        self.assertEqual(2, len(result))
        mock_env_list.assert_called_once_with(status=None)

    @mock.patch("rally.common.db.env_create")
    def test__validate_and_create_env_empty_spec(self, mock_env_create):
        mock_env_create.return_value = {"uuid": "1"}
        env = env_mgr.EnvManager._validate_and_create_env(
            "name", "descr", {"extras": ""}, {})

        self.assertIsInstance(env, env_mgr.EnvManager)
        self.assertEqual("1", env.uuid)
        mock_env_create.assert_called_once_with(
            "name", env_mgr.STATUS.INIT, "descr", {"extras": ""}, {}, [])

    @mock.patch("rally.common.db.env_create")
    def test__validate_and_create_env_with_spec(self, mock_env_create):
        mock_env_create.return_value = {"uuid": "1"}

        @platform.configure("existing", platform="valid1")
        class Platform1(platform.Platform):
            CONFIG_SCHEMA = {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": False
            }

        @platform.configure("2", platform="valid2")
        class Platform2(platform.Platform):
            CONFIG_SCHEMA = {
                "type": "object",
                "properties": {"b": {"type": "string"}},
                "additionalProperties": False
            }

        self.addCleanup(Platform1.unregister)
        self.addCleanup(Platform2.unregister)

        env_mgr.EnvManager._validate_and_create_env(
            "n", "d", "ext", {"valid1": {"a": "str"}})

        expected_platforms = [{
            "status": platform.STATUS.INIT,
            "plugin_name": "existing@valid1",
            "plugin_spec": {"a": "str"},
            "platform_name": "valid1"
        }]

        mock_env_create.assert_called_once_with(
            "n", env_mgr.STATUS.INIT, "d", "ext",
            {"existing@valid1": {"a": "str"}}, expected_platforms)

        mock_env_create.reset_mock()
        self.assertRaises(
            exceptions.ManagerInvalidSpec,
            env_mgr.EnvManager._validate_and_create_env,
            "n", "d", "ext", {"valid1": {"a": "str"}, "2@valid2": {"c": 1}}
        )
        self.assertFalse(mock_env_create.called)

        mock_env_create.reset_mock()
        self.assertRaises(
            exceptions.RallyException,
            env_mgr.EnvManager._validate_and_create_env,
            "n", "d", "ext", {"non_existing@nope": {"a": "str"}}
        )
        self.assertFalse(mock_env_create.called)

    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.common.db.platform_set_data")
    @mock.patch("rally.common.db.platform_set_status")
    @mock.patch("rally.common.db.platforms_list")
    def test__create_platforms(self,
                               mock_platforms_list, mock_platform_set_status,
                               mock_platform_set_data, mock_env_set_status):

        # One platform that passes successfully
        @platform.configure("passes", platform="create")
        class ValidPlatform(platform.Platform):
            def create(self):
                return {"platform": "data"}, {"plugin": "data"}

        self.addCleanup(ValidPlatform.unregister)
        mock_platforms_list.return_value = [
            {
                "uuid": "p_uuid",
                "plugin_name": "passes@create",
                "plugin_spec": {},
                "plugin_data": None,
                "platform_data": None,
                "status": platform.STATUS.INIT
            }
        ]
        env_mgr.EnvManager({"uuid": 121})._create_platforms()

        mock_platforms_list.assert_called_once_with(121)
        mock_platform_set_status.assert_called_once_with(
            "p_uuid", platform.STATUS.INIT, platform.STATUS.READY)
        mock_platform_set_data.assert_called_once_with(
            "p_uuid",
            platform_data={"platform": "data"}, plugin_data={"plugin": "data"})
        mock_env_set_status.assert_called_once_with(
            121, env_mgr.STATUS.INIT, env_mgr.STATUS.READY)

    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.common.db.platform_set_status")
    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test__create_platforms_failed(self, mock__get_platforms,
                                      mock_platform_set_status,
                                      mock_env_set_status):
        # Check when first fails, second is marked as skipped

        @platform.configure("bad", platform="create")
        class InValidPlatform(platform.Platform):
            def create(self):
                raise Exception("I don't want to work!")

        @platform.configure("good_but_skipped", platform="create")
        class ValidPlatform(platform.Platform):
            def create(self):
                return {"platform": "data"}, {"plugin": "data"}

        for p in [InValidPlatform, ValidPlatform]:
            self.addCleanup(p.unregister)

        mock__get_platforms.return_value = [
            InValidPlatform({}, uuid=1), ValidPlatform({}, uuid=2)]

        env_mgr.EnvManager({"uuid": 42})._create_platforms()

        mock_env_set_status.assert_called_once_with(
            42, env_mgr.STATUS.INIT, env_mgr.STATUS.FAILED_TO_CREATE)

        mock_platform_set_status.assert_has_calls([
            mock.call(1, platform.STATUS.INIT,
                      platform.STATUS.FAILED_TO_CREATE),
            mock.call(2, platform.STATUS.INIT, platform.STATUS.SKIPPED),
        ])

    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.common.db.platform_set_status")
    @mock.patch("rally.common.db.platform_set_data")
    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test__create_platforms_when_db_issues_autodestroy(
            self, mock__get_platforms, mock_platform_set_data,
            mock_platform_set_status, mock_env_set_status):
        # inject db errors check that auto destroy is called
        platform1 = mock.MagicMock()
        platform1.uuid = 11
        platform1.destroy.side_effect = Exception
        platform1.create.return_value = ("platform_d", "plugin_d")
        platform2 = mock.MagicMock()
        platform2.uuid = 22
        mock__get_platforms.return_value = [platform1, platform2]
        mock_platform_set_data.side_effect = Exception

        env_mgr.EnvManager({"uuid": 42})._create_platforms()

        mock_platform_set_status.assert_called_once_with(
            22, platform.STATUS.INIT, platform.STATUS.SKIPPED)
        mock_platform_set_data.assert_called_once_with(
            11, platform_data="platform_d", plugin_data="plugin_d")
        mock_env_set_status.assert_called_once_with(
            42, env_mgr.STATUS.INIT, env_mgr.STATUS.FAILED_TO_CREATE)

    @mock.patch("rally.common.db.platforms_list", return_value=[])
    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.common.db.env_create", return_value={"uuid": 121})
    def test_create(self, mock_env_create, mock_env_set_status,
                    mock_platforms_list):
        # NOTE(boris-42): Just check with empty spec that just check workflow
        result = env_mgr.EnvManager.create("a", "descr", "extras", {})

        self.assertIsInstance(result, env_mgr.EnvManager)
        self.assertEqual(121, result.uuid)

    @mock.patch("rally.common.db.env_rename")
    def test_rename(self, mock_env_rename):
        env = env_mgr.EnvManager({"uuid": "11", "name": "n"})

        self.assertTrue(env.rename, env.rename("n"))
        self.assertEqual(0, mock_env_rename.call_count)
        self.assertTrue(env.rename, env.rename("n2"))
        mock_env_rename.assert_called_once_with("11", "n", "n2")

    @mock.patch("rally.common.db.env_update")
    def test_update(self, mock_env_update):
        env = env_mgr.EnvManager(
            {"uuid": "11", "description": "d", "extras": "e"})

        self.assertTrue(env.update())
        self.assertEqual(0, mock_env_update.call_count)

        env.update(description="d2", extras="e2")
        mock_env_update.assert_called_once_with(
            "11", description="d2", extras="e2")

    def test_update_spec(self):
        self.assertRaises(NotImplementedError,
                          env_mgr.EnvManager({"uuid": 1}).update_spec, "")

    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test_check_health(self, mock__get_platforms):

        valid_result = {
            "available": False,
            "message": "Nope I don't want to work"
        }

        @platform.configure(name="valid", platform="check")
        class ValidPlatform(platform.Platform):

            def check_health(self):
                return valid_result

        @platform.configure(name="broken_fromat", platform="check")
        class BrokenFormatPlatform(platform.Platform):

            def check_health(self):
                return {"something": "is wrong here in format"}

        @platform.configure(name="just_broken", platform="check")
        class JustBrokenPlatform(platform.Platform):

            def check_health(self):
                raise Exception("This is really bad exception")

        for p in [ValidPlatform, BrokenFormatPlatform, JustBrokenPlatform]:
            self.addCleanup(p.unregister)

        mock__get_platforms.side_effect = [
            [ValidPlatform("spec1")],
            [ValidPlatform("spec1"), BrokenFormatPlatform("spec2")],
            [JustBrokenPlatform("spec3")]
        ]

        self.assertEqual({"valid@check": valid_result},
                         env_mgr.EnvManager({"uuid": "42"}).check_health())

        broken_msg = "Plugin %s.check_health() method is broken"

        self.assertEqual(
            {
                "valid@check": valid_result,
                "broken_fromat@check": {
                    "message": broken_msg % "broken_fromat@check",
                    "available": False
                }
            },
            env_mgr.EnvManager({"uuid": "43"}).check_health())

        self.assertEqual(
            {
                "just_broken@check": {
                    "message": broken_msg % "just_broken@check",
                    "available": False,
                    "traceback": (Exception, mock.ANY, mock.ANY)
                }
            },
            env_mgr.EnvManager({"uuid": "44"}).check_health())

        mock__get_platforms.assert_has_calls([mock.call()] * 3)

    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test_get_info(self, mock__get_platforms):

        @platform.configure(name="valid", platform="info")
        class InfoValid(platform.Platform):

            def info(self):
                return {"info": "it works!", "error": ""}

        @platform.configure(name="wrong_fmt", platform="info")
        class InfoWrongFormat(platform.Platform):

            def info(self):
                return {"something": "is wrong"}

        @platform.configure(name="broken", platform="info")
        class InfoBroken(platform.Platform):

            def info(self):
                raise Exception("This should not happen")

        for p in [InfoValid, InfoWrongFormat, InfoBroken]:
            self.addCleanup(p.unregister)

        mock__get_platforms.side_effect = [
            [InfoValid("spec1")],
            [InfoValid("spec1"), InfoWrongFormat("spec2")],
            [InfoValid("spec1"), InfoBroken("spec3")],
        ]

        valid_result = {"info": "it works!", "error": ""}

        self.assertEqual({"valid@info": valid_result},
                         env_mgr.EnvManager({"uuid": "42"}).get_info())

        self.assertEqual(
            {
                "valid@info": valid_result,
                "wrong_fmt@info": {
                    "error": "Plugin wrong_fmt@info.info() method is broken",
                    "info": None
                }
            },
            env_mgr.EnvManager({"uuid": "43"}).get_info())

        self.assertEqual(
            {
                "valid@info": valid_result,
                "broken@info": {
                    "error": "Plugin broken@info.info() method is broken",
                    "info": None,
                    "traceback": (Exception, mock.ANY, mock.ANY)
                }
            },
            env_mgr.EnvManager({"uuid": "44"}).get_info())

        mock__get_platforms.assert_has_calls([mock.call()] * 3)

    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test_cleanup(self, mock__get_platforms, mock_env_set_status):

        valid_result = {
            "discovered": 10,
            "deleted": 6,
            "failed": 4,
            "resources": {
                "vm": {
                    "discovered": 2,
                    "failed": 2,
                    "deleted": 0
                }
            },
            "errors": [
                {
                    "resource_id": "1",
                    "resource_type": "vm",
                    "message": "something"
                }
            ]
        }

        @platform.configure(name="valid", platform="clean")
        class CleanValid(platform.Platform):

            def cleanup(self, task_uuid=None):
                return valid_result

        @platform.configure(name="wrong", platform="clean")
        class CleanWrongFormat(platform.Platform):

            def cleanup(self, task_uuid):
                return {"something": "is wrong"}

        @platform.configure(name="broken", platform="clean")
        class CleanBroken(platform.Platform):

            def cleanup(self, task_uuid):
                raise Exception("This should not happen")

        for p in [CleanValid, CleanWrongFormat, CleanBroken]:
            self.addCleanup(p.unregister)

        mock__get_platforms.return_value = [
            CleanValid("spec1"),
            CleanBroken("spec2"),
            CleanWrongFormat("spec3")
        ]

        result = env_mgr.EnvManager({"uuid": 424}).cleanup()
        mock__get_platforms.assert_called_once_with()
        mock_env_set_status.assert_has_calls([
            mock.call(424, env_mgr.STATUS.READY, env_mgr.STATUS.CLEANING),
            mock.call(424, env_mgr.STATUS.CLEANING, env_mgr.STATUS.READY)
        ])
        self.assertIsInstance(result, dict)
        self.assertEqual(3, len(result))
        self.assertEqual(valid_result, result["valid@clean"])
        self.assertEqual(
            {
                "discovered": 0, "deleted": 0, "failed": 0, "resources": {},
                "errors": [{
                    "message": "Plugin wrong@clean.cleanup() method is broken",
                }]
            },
            result["wrong@clean"]
        )
        self.assertEqual(
            {
                "discovered": 0, "deleted": 0, "failed": 0, "resources": {},
                "errors": [{
                    "message": "Plugin broken@clean.cleanup() method is "
                               "broken",
                    "traceback": (Exception, mock.ANY, mock.ANY)
                }]
            },
            result["broken@clean"]
        )

    @mock.patch("rally.env.env_mgr.EnvManager.cleanup",
                return_value={"errors": [121]})
    def test_destory_cleanup_failed(self, mock_env_manager_cleanup):
        self.assertEqual(
            {
                "cleanup_info": {
                    "errors": [121],
                    "skipped": False
                },
                "destroy_info": {
                    "skipped": True,
                    "platforms": {},
                    "message": "Skipped because cleanup failed"
                }
            },
            env_mgr.EnvManager({"uuid": 42}).destroy()
        )
        mock_env_manager_cleanup.assert_called_once_with()

    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms", return_value=[])
    @mock.patch("rally.common.db.env_set_status")
    def test_destroy_no_platforms(self,
                                  mock_env_set_status, mock__get_platforms):

        self.assertEqual(
            {
                "cleanup_info": {"skipped": True},
                "destroy_info": {"skipped": False, "platforms": {}}
            },
            env_mgr.EnvManager({"uuid": 42}).destroy(skip_cleanup=True)
        )
        mock_env_set_status.assert_has_calls([
            mock.call(42, env_mgr.STATUS.READY, env_mgr.STATUS.DESTROYING),
            mock.call(42, env_mgr.STATUS.DESTROYING, env_mgr.STATUS.DESTROYED)
        ])
        mock__get_platforms.assert_called_once_with()

    @mock.patch("rally.common.db.env_set_status")
    @mock.patch("rally.common.db.platform_set_status")
    @mock.patch("rally.env.env_mgr.EnvManager._get_platforms")
    def test_destory_with_platforms(self, mock__get_platforms,
                                    mock_platform_set_status,
                                    mock_env_set_status):
        platform1 = mock.MagicMock()
        platform1.get_fullname.return_value = "p_destroyed"
        platform1.status = platform.STATUS.DESTROYED

        platform2 = mock.MagicMock()
        platform2.get_fullname.return_value = "p_valid"
        platform2.status = platform.STATUS.READY

        platform3 = mock.MagicMock()
        platform3.get_fullname.return_value = "p_invalid"
        platform3.destroy.side_effect = Exception
        platform3.status = platform.STATUS.READY

        mock__get_platforms.return_value = [
            platform1, platform2, platform3
        ]

        result = env_mgr.EnvManager({"uuid": 666}).destroy(skip_cleanup=True)
        self.assertIsInstance(result, dict)
        self.assertEqual(2, len(result))
        self.assertEqual({"skipped": True}, result["cleanup_info"])
        self.assertEqual(
            {
                "skipped": False,
                "platforms": {
                    "p_destroyed": {
                        "message": "Platform is already destroyed. Do nothing",
                        "status": {
                            "old": platform.STATUS.DESTROYED,
                            "new": platform.STATUS.DESTROYED
                        },
                    },
                    "p_valid": {
                        "message": "Successfully destroyed",
                        "status": {
                            "old": platform.STATUS.READY,
                            "new": platform.STATUS.DESTROYED
                        },
                    },
                    "p_invalid": {
                        "message": "Failed to destroy",
                        "status": {
                            "old": platform.STATUS.READY,
                            "new": platform.STATUS.FAILED_TO_DESTROY
                        },
                        "traceback": (Exception, mock.ANY, mock.ANY)
                    }
                }
            },
            result["destroy_info"])

        mock__get_platforms.assert_called_once_with()
        mock_platform_set_status.assert_has_calls([
            mock.call(platform2.uuid,
                      platform.STATUS.READY,
                      platform.STATUS.DESTROYING),
            mock.call(platform2.uuid,
                      platform.STATUS.DESTROYING,
                      platform.STATUS.DESTROYED),
            mock.call(platform3.uuid,
                      platform.STATUS.READY,
                      platform.STATUS.DESTROYING),
            mock.call(platform3.uuid,
                      platform.STATUS.DESTROYING,
                      platform.STATUS.FAILED_TO_DESTROY)
        ])

    @mock.patch("rally.common.db.env_get_status")
    @mock.patch("rally.common.db.env_delete_cascade")
    def test_delete(self, mock_env_delete_cascade, mock_env_get_status):
        mock_env_get_status.side_effect = [
            "WRONG", env_mgr.STATUS.DESTROYED
        ]
        self.assertRaises(exceptions.ManagerInvalidState,
                          env_mgr.EnvManager({"uuid": "42"}).delete)
        self.assertFalse(mock_env_delete_cascade.called)

        env_mgr.EnvManager({"uuid": "43"}).delete()
        mock_env_delete_cascade.assert_called_once_with("43")

        mock_env_get_status.assert_has_calls(
            [mock.call("42"), mock.call("43")])

    @mock.patch("rally.common.db.env_get_status")
    @mock.patch("rally.common.db.env_delete_cascade")
    def test_delete_force(self, mock_env_delete_cascade, mock_env_get_status):
        mock_env_get_status.return_value = "WRONG"
        env_mgr.EnvManager({"uuid": "44"}).delete(force=True)
        mock_env_delete_cascade.assert_called_once_with("44")
