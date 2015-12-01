# Copyright 2015: Mirantis Inc.
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
from oslo_config import cfg

from rally.plugins.openstack.scenarios.murano import utils
from tests.unit import test

MRN_UTILS = "rally.plugins.openstack.scenarios.murano.utils"
CONF = cfg.CONF


class MuranoScenarioTestCase(test.ScenarioTestCase):

    def test_list_environments(self):
        self.clients("murano").environments.list.return_value = []
        scenario = utils.MuranoScenario(context=self.context)
        return_environments_list = scenario._list_environments()
        self.assertEqual([], return_environments_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.list_environments")

    def test_create_environments(self):
        self.clients("murano").environments.create = mock.Mock()
        scenario = utils.MuranoScenario(context=self.context)
        scenario.generate_random_name = mock.Mock()

        create_env = scenario._create_environment()
        self.assertEqual(
            create_env,
            self.clients("murano").environments.create.return_value)
        self.clients("murano").environments.create.assert_called_once_with(
            {"name": scenario.generate_random_name.return_value})
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_environment")

    def test_delete_environment(self):
        environment = mock.Mock(id="id")
        self.clients("murano").environments.delete.return_value = "ok"
        scenario = utils.MuranoScenario(context=self.context)
        scenario._delete_environment(environment)
        self.clients("murano").environments.delete.assert_called_once_with(
            environment.id
        )

    def test_create_session(self):
        self.clients("murano").sessions.configure.return_value = "sess"
        scenario = utils.MuranoScenario(context=self.context)
        create_sess = scenario._create_session("id")
        self.assertEqual("sess", create_sess)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_session")

    def test__create_service(self,):
        self.clients("murano").services.post.return_value = "app"
        mock_env = mock.Mock(id="ip")
        mock_sess = mock.Mock(id="ip")
        scenario = utils.MuranoScenario(context=self.context)

        create_app = scenario._create_service(mock_env, mock_sess,
                                              "fake_full_name",
                                              atomic_action=True)

        self.assertEqual("app", create_app)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_service")

    def test_deploy_environment(self):
        environment = mock.Mock(id="id")
        session = mock.Mock(id="id")
        self.clients("murano").sessions.deploy.return_value = "ok"
        scenario = utils.MuranoScenario(context=self.context)
        scenario._deploy_environment(environment, session)

        self.clients("murano").sessions.deploy.assert_called_once_with(
            environment.id, session.id
        )

        config = CONF.benchmark
        self.mock_wait_for.mock.assert_called_once_with(
            environment,
            update_resource=self.mock_get_from_manager.mock.return_value,
            ready_statuses=["READY"],
            check_interval=config.murano_deploy_environment_check_interval,
            timeout=config.murano_deploy_environment_timeout)
        self.mock_get_from_manager.mock.assert_called_once_with(
            ["DEPLOY FAILURE"])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.deploy_environment")

    @mock.patch(MRN_UTILS + ".open",
                side_effect=mock.mock_open(read_data="Key: value"),
                create=True)
    def test_read_from_file(self, mock_open):
        utility = utils.MuranoPackageManager({"uuid": "fake_task_id"})
        data = utility._read_from_file("filename")
        expected_data = {"Key": "value"}
        self.assertEqual(expected_data, data)

    @mock.patch(MRN_UTILS + ".MuranoPackageManager._read_from_file")
    @mock.patch(MRN_UTILS + ".MuranoPackageManager._write_to_file")
    def test_change_app_fullname(
            self, mock_murano_package_manager__write_to_file,
            mock_murano_package_manager__read_from_file):
        manifest = {"FullName": "app.name_abc",
                    "Classes": {"app.name_abc": "app_class.yaml"}}
        mock_murano_package_manager__read_from_file.side_effect = (
            [manifest])
        utility = utils.MuranoPackageManager({"uuid": "fake_task_id"})
        utility._change_app_fullname("tmp/tmpfile/")
        mock_murano_package_manager__read_from_file.assert_has_calls(
            [mock.call("tmp/tmpfile/manifest.yaml")]
        )
        mock_murano_package_manager__write_to_file.assert_has_calls(
            [mock.call(manifest, "tmp/tmpfile/manifest.yaml")]
        )

    @mock.patch("zipfile.is_zipfile")
    @mock.patch("tempfile.mkdtemp")
    @mock.patch("shutil.copytree")
    @mock.patch(MRN_UTILS + ".MuranoPackageManager._change_app_fullname")
    @mock.patch("rally.common.fileutils.pack_dir")
    @mock.patch("shutil.rmtree")
    def test_prepare_zip_if_not_zip(
            self, mock_shutil_rmtree, mock_pack_dir,
            mock_murano_package_manager__change_app_fullname,
            mock_shutil_copytree, mock_tempfile_mkdtemp,
            mock_zipfile_is_zipfile):
        utility = utils.MuranoPackageManager({"uuid": "fake_task_id"})
        package_path = "tmp/tmpfile"

        mock_zipfile_is_zipfile.return_value = False
        mock_tempfile_mkdtemp.return_value = "tmp/tmpfile"
        mock_pack_dir.return_value = "tmp/tmpzipfile"

        zip_file = utility._prepare_package(package_path)

        self.assertEqual("tmp/tmpzipfile", zip_file)
        mock_tempfile_mkdtemp.assert_called_once_with()
        mock_shutil_copytree.assert_called_once_with(
            "tmp/tmpfile",
            "tmp/tmpfile/package/"
        )
        (mock_murano_package_manager__change_app_fullname.
            assert_called_once_with("tmp/tmpfile/package/"))
        mock_shutil_rmtree.assert_called_once_with("tmp/tmpfile")

    @mock.patch("zipfile.is_zipfile")
    def test_prepare_zip_if_zip(self, mock_zipfile_is_zipfile):
        utility = utils.MuranoPackageManager({"uuid": "fake_task_id"})
        package_path = "tmp/tmpfile.zip"
        mock_zipfile_is_zipfile.return_value = True
        zip_file = utility._prepare_package(package_path)
        self.assertEqual("tmp/tmpfile.zip", zip_file)

    def test_list_packages(self):
        scenario = utils.MuranoScenario()
        self.assertEqual(self.clients("murano").packages.list.return_value,
                         scenario._list_packages())
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.list_packages")

    @mock.patch(MRN_UTILS + ".open", create=True)
    def test_import_package(self, mock_open):
        self.clients("murano").packages.create.return_value = (
            "created_foo_package"
        )
        scenario = utils.MuranoScenario()
        mock_open.return_value = "opened_foo_package.zip"
        imp_package = scenario._import_package("foo_package.zip")
        self.assertEqual("created_foo_package", imp_package)
        self.clients("murano").packages.create.assert_called_once_with(
            {}, {"file": "opened_foo_package.zip"})
        mock_open.assert_called_once_with("foo_package.zip")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.import_package")

    def test_delete_package(self):
        package = mock.Mock(id="package_id")
        scenario = utils.MuranoScenario()
        scenario._delete_package(package)
        self.clients("murano").packages.delete.assert_called_once_with(
            "package_id"
        )
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.delete_package")

    def test_update_package(self):
        package = mock.Mock(id="package_id")
        self.clients("murano").packages.update.return_value = "updated_package"
        scenario = utils.MuranoScenario()
        upd_package = scenario._update_package(
            package, {"tags": ["tag"]}, "add"
        )
        self.assertEqual("updated_package", upd_package)
        self.clients("murano").packages.update.assert_called_once_with(
            "package_id",
            {"tags": ["tag"]},
            "add"
        )
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.update_package")

    def test_filter_packages(self):
        self.clients("murano").packages.filter.return_value = []
        scenario = utils.MuranoScenario()
        return_apps_list = scenario._filter_applications(
            {"category": "Web"}
        )
        self.assertEqual([], return_apps_list)
        self.clients("murano").packages.filter.assert_called_once_with(
            category="Web"
        )
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.filter_applications")
