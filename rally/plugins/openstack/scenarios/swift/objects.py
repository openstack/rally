# Copyright 2015: Cisco Systems, Inc.
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

import tempfile

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.swift import utils
from rally.task import validation


"""Scenarios for Swift Objects."""


@validation.add("required_services", services=[consts.Service.SWIFT])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["swift"]},
    name="SwiftObjects.create_container_and_object_then_list_objects",
    platform="openstack")
class CreateContainerAndObjectThenListObjects(utils.SwiftScenario):

    def run(self, objects_per_container=1, object_size=1024, **kwargs):
        """Create container and objects then list all objects.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """

        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            for i in range(objects_per_container):
                dummy_file.seek(0)
                self._upload_object(container_name, dummy_file)
        self._list_objects(container_name)


@validation.add("required_services", services=[consts.Service.SWIFT])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["swift"]},
    name="SwiftObjects.create_container_and_object_then_delete_all",
    platform="openstack")
class CreateContainerAndObjectThenDeleteAll(utils.SwiftScenario):

    def run(self, objects_per_container=1, object_size=1024, **kwargs):
        """Create container and objects then delete everything created.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """
        container_name = None
        objects_list = []
        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            for i in range(objects_per_container):
                dummy_file.seek(0)
                object_name = self._upload_object(container_name,
                                                  dummy_file)[1]
                objects_list.append(object_name)

        for object_name in objects_list:
            self._delete_object(container_name, object_name)
        self._delete_container(container_name)


@validation.add("required_services", services=[consts.Service.SWIFT])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"cleanup@openstack": ["swift"]},
    name="SwiftObjects.create_container_and_object_then_download_object",
    platform="openstack")
class CreateContainerAndObjectThenDownloadObject(utils.SwiftScenario):

    def run(self, objects_per_container=1, object_size=1024, **kwargs):
        """Create container and objects then download all objects.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """
        container_name = None
        objects_list = []
        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            for i in range(objects_per_container):
                dummy_file.seek(0)
                object_name = self._upload_object(container_name,
                                                  dummy_file)[1]
                objects_list.append(object_name)

        for object_name in objects_list:
            self._download_object(container_name, object_name)


@validation.add("required_services", services=[consts.Service.SWIFT])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"swift_objects@openstack": {}},
    name="SwiftObjects.list_objects_in_containers",
    platform="openstack")
class ListObjectsInContainers(utils.SwiftScenario):

    def run(self):
        """List objects in all containers."""

        containers = self._list_containers()[1]

        for container in containers:
            self._list_objects(container["name"])


@validation.add("required_services", services=[consts.Service.SWIFT])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(
    context={"swift_objects@openstack": {}},
    name="SwiftObjects.list_and_download_objects_in_containers",
    platform="openstack")
class ListAndDownloadObjectsInContainers(utils.SwiftScenario):

    def run(self):
        """List and download objects in all containers."""

        containers = self._list_containers()[1]

        objects_dict = {}
        for container in containers:
            container_name = container["name"]
            objects_dict[container_name] = self._list_objects(
                container_name)[1]

        for container_name, objects in objects_dict.items():
            for obj in objects:
                self._download_object(container_name, obj["name"])
