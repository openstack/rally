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
from rally.task import atomic
from rally.task import validation


class SwiftObjects(utils.SwiftScenario):
    """Benchmark scenarios for Swift Objects."""

    @validation.required_services(consts.Service.SWIFT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["swift"]})
    def create_container_and_object_then_list_objects(
            self, objects_per_container=1,
            object_size=1024, **kwargs):
        """Create container and objects then list all objects.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """
        key_suffix = "object"
        if objects_per_container > 1:
            key_suffix = "%i_objects" % objects_per_container

        container_name = None
        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            with atomic.ActionTimer(self, "swift.create_%s" % key_suffix):
                for i in range(objects_per_container):
                    dummy_file.seek(0)
                    self._upload_object(container_name, dummy_file,
                                        atomic_action=False)
        self._list_objects(container_name)

    @validation.required_services(consts.Service.SWIFT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["swift"]})
    def create_container_and_object_then_delete_all(
            self, objects_per_container=1,
            object_size=1024, **kwargs):
        """Create container and objects then delete everything created.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """
        key_suffix = "object"
        if objects_per_container > 1:
            key_suffix = "%i_objects" % objects_per_container

        container_name = None
        objects_list = []
        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            with atomic.ActionTimer(self, "swift.create_%s" % key_suffix):
                for i in range(objects_per_container):
                    dummy_file.seek(0)
                    object_name = self._upload_object(container_name,
                                                      dummy_file,
                                                      atomic_action=False)[1]
                    objects_list.append(object_name)

        with atomic.ActionTimer(self, "swift.delete_%s" % key_suffix):
            for object_name in objects_list:
                self._delete_object(container_name, object_name,
                                    atomic_action=False)
        self._delete_container(container_name)

    @validation.required_services(consts.Service.SWIFT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["swift"]})
    def create_container_and_object_then_download_object(
            self, objects_per_container=1,
            object_size=1024, **kwargs):
        """Create container and objects then download all objects.

        :param objects_per_container: int, number of objects to upload
        :param object_size: int, temporary local object size
        :param kwargs: dict, optional parameters to create container
        """
        key_suffix = "object"
        if objects_per_container > 1:
            key_suffix = "%i_objects" % objects_per_container

        container_name = None
        objects_list = []
        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)
            container_name = self._create_container(**kwargs)
            with atomic.ActionTimer(self, "swift.create_%s" % key_suffix):
                for i in range(objects_per_container):
                    dummy_file.seek(0)
                    object_name = self._upload_object(container_name,
                                                      dummy_file,
                                                      atomic_action=False)[1]
                    objects_list.append(object_name)

        with atomic.ActionTimer(self, "swift.download_%s" % key_suffix):
            for object_name in objects_list:
                self._download_object(container_name, object_name,
                                      atomic_action=False)

    @validation.required_services(consts.Service.SWIFT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"swift_objects": {}})
    def list_objects_in_containers(self):
        """List objects in all containers."""
        containers = self._list_containers()[1]

        key_suffix = "container"
        if len(containers) > 1:
            key_suffix = "%i_containers" % len(containers)

        with atomic.ActionTimer(self, "swift.list_objects_in_%s" % key_suffix):
            for container in containers:
                self._list_objects(container["name"], atomic_action=False)

    @validation.required_services(consts.Service.SWIFT)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"swift_objects": {}})
    def list_and_download_objects_in_containers(self):
        """List and download objects in all containers."""
        containers = self._list_containers()[1]

        list_key_suffix = "container"
        if len(containers) > 1:
            list_key_suffix = "%i_containers" % len(containers)

        objects_dict = {}
        with atomic.ActionTimer(self,
                                "swift.list_objects_in_%s" % list_key_suffix):
            for container in containers:
                container_name = container["name"]
                objects_dict[container_name] = self._list_objects(
                    container_name,
                    atomic_action=False)[1]

        objects_total = sum(map(len, objects_dict.values()))
        download_key_suffix = "object"
        if objects_total > 1:
            download_key_suffix = "%i_objects" % objects_total

        with atomic.ActionTimer(self,
                                "swift.download_%s" % download_key_suffix):
            for container_name, objects in objects_dict.items():
                for obj in objects:
                    self._download_object(container_name, obj["name"],
                                          atomic_action=False)
