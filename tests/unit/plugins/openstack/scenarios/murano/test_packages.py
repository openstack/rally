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

from rally.plugins.openstack.scenarios.murano import packages
from tests.unit import test

MURANO_SCENARIO = ("rally.plugins.openstack.scenarios.murano."
                   "packages.MuranoPackages")


class MuranoPackagesTestCase(test.TestCase):

    def setUp(self):
        super(MuranoPackagesTestCase, self).setUp()
        self.mock_remove = mock.patch("os.remove")
        self.mock_remove.start()

    def tearDown(self):
        super(MuranoPackagesTestCase, self).tearDown()
        self.mock_remove.stop()

    def mock_modules(self, scenario):
        scenario._import_package = mock.Mock()
        scenario._zip_package = mock.Mock()
        scenario._list_packages = mock.Mock()
        scenario._delete_package = mock.Mock()
        scenario._update_package = mock.Mock()
        scenario._filter_applications = mock.Mock()

    def test_make_zip_import_and_list_packages(self):
        scenario = packages.ImportAndListPackages()
        self.mock_modules(scenario)
        scenario.run("foo_package.zip")
        scenario._import_package.assert_called_once_with(
            scenario._zip_package.return_value)
        scenario._zip_package.assert_called_once_with("foo_package.zip")
        scenario._list_packages.assert_called_once_with(
            include_disabled=False)

    def test_import_and_delete_package(self):
        scenario = packages.ImportAndDeletePackage()
        self.mock_modules(scenario)
        fake_package = mock.Mock()
        scenario._import_package.return_value = fake_package
        scenario.run("foo_package.zip")
        scenario._import_package.assert_called_once_with(
            scenario._zip_package.return_value)
        scenario._delete_package.assert_called_once_with(fake_package)

    def test_package_lifecycle(self):
        scenario = packages.PackageLifecycle()
        self.mock_modules(scenario)
        fake_package = mock.Mock()
        scenario._import_package.return_value = fake_package
        scenario.run("foo_package.zip", {"category": "Web"}, "add")
        scenario._import_package.assert_called_once_with(
            scenario._zip_package.return_value)
        scenario._update_package.assert_called_once_with(
            fake_package, {"category": "Web"}, "add")
        scenario._delete_package.assert_called_once_with(fake_package)

    def test_import_and_filter_applications(self):
        scenario = packages.ImportAndFilterApplications()
        self.mock_modules(scenario)
        fake_package = mock.Mock()
        scenario._import_package.return_value = fake_package
        scenario.run("foo_package.zip", {"category": "Web"})
        scenario._import_package.assert_called_once_with(
            scenario._zip_package.return_value)
        scenario._filter_applications.assert_called_once_with(
            {"category": "Web"}
        )