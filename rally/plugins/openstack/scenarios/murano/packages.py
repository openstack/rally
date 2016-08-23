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


import os

from rally import consts
from rally.plugins.openstack.scenarios.murano import utils
from rally.task import scenario
from rally.task import validation


"""Scenarios for Murano packages."""


@validation.required_parameters("package")
@validation.file_exists(param_name="package", mode=os.F_OK)
@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["murano.packages"]},
                    name="MuranoPackages.import_and_list_packages")
class ImportAndListPackages(utils.MuranoScenario):

    def run(self, package, include_disabled=False):
        """Import Murano package and get list of packages.

        Measure the "murano import-package" and "murano package-list" commands
        performance.
        It imports Murano package from "package" (if it is not a zip archive
        then zip archive will be prepared) and gets list of imported packages.

        :param package: path to zip archive that represents Murano
                        application package or absolute path to folder with
                        package components
        :param include_disabled: specifies whether the disabled packages will
                                 be included in a the result or not.
                                 Default value is False.
        """
        package_path = self._zip_package(package)
        try:
            self._import_package(package_path)
            self._list_packages(include_disabled=include_disabled)
        finally:
            os.remove(package_path)


@validation.required_parameters("package")
@validation.file_exists(param_name="package", mode=os.F_OK)
@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["murano.packages"]},
                    name="MuranoPackages.import_and_delete_package")
class ImportAndDeletePackage(utils.MuranoScenario):

    def run(self, package):
        """Import Murano package and then delete it.

        Measure the "murano import-package" and "murano package-delete"
        commands performance.
        It imports Murano package from "package" (if it is not a zip archive
        then zip archive will be prepared) and deletes it.

        :param package: path to zip archive that represents Murano
                        application package or absolute path to folder with
                        package components
        """
        package_path = self._zip_package(package)
        try:
            package = self._import_package(package_path)
            self._delete_package(package)
        finally:
            os.remove(package_path)


@validation.required_parameters("package", "body")
@validation.file_exists(param_name="package", mode=os.F_OK)
@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["murano.packages"]},
                    name="MuranoPackages.package_lifecycle")
class PackageLifecycle(utils.MuranoScenario):

    def run(self, package, body, operation="replace"):
        """Import Murano package, modify it and then delete it.

        Measure the Murano import, update and delete package
        commands performance.
        It imports Murano package from "package" (if it is not a zip archive
        then zip archive will be prepared), modifies it (using data from
        "body") and deletes.

        :param package: path to zip archive that represents Murano
                        application package or absolute path to folder with
                        package components
        :param body: dict object that defines what package property will be
                     updated, e.g {"tags": ["tag"]} or {"enabled": "true"}
        :param operation: string object that defines the way of how package
                          property will be updated, allowed operations are
                          "add", "replace" or "delete".
                          Default value is "replace".

        """
        package_path = self._zip_package(package)
        try:
            package = self._import_package(package_path)
            self._update_package(package, body, operation)
            self._delete_package(package)
        finally:
            os.remove(package_path)


@validation.required_parameters("package", "filter_query")
@validation.file_exists(param_name="package", mode=os.F_OK)
@validation.required_clients("murano")
@validation.required_services(consts.Service.MURANO)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["murano.packages"]},
                    name="MuranoPackages.import_and_filter_applications")
class ImportAndFilterApplications(utils.MuranoScenario):

    def run(self, package, filter_query):
        """Import Murano package and then filter packages by some criteria.

        Measure the performance of package import and package
        filtering commands.
        It imports Murano package from "package" (if it is not a zip archive
        then zip archive will be prepared) and filters packages by some
        criteria.

        :param package: path to zip archive that represents Murano
                        application package or absolute path to folder with
                        package components
        :param filter_query: dict that contains filter criteria, lately it
                             will be passed as **kwargs to filter method
                             e.g. {"category": "Web"}
        """
        package_path = self._zip_package(package)
        try:
            self._import_package(package_path)
            self._filter_applications(filter_query)
        finally:
            os.remove(package_path)