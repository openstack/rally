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

from rally.plugins.openstack import scenario
from rally.task import atomic


class SwiftScenario(scenario.OpenStackScenario):
    """Base class for Swift scenarios with basic atomic actions."""

    @atomic.action_timer("swift.list_containers")
    def _list_containers(self, full_listing=True, **kwargs):
        """Return list of containers.

        :param full_listing: bool, enable unlimit number of listing returned
        :param kwargs: dict, other optional parameters to get_account

        :returns: tuple, (dict of response headers, a list of containers)
        """
        return self.clients("swift").get_account(full_listing=full_listing,
                                                 **kwargs)

    def _create_container(self, container_name=None, public=False,
                          atomic_action=True, **kwargs):
        """Create a new container with given name.

        :param container_name: str, name of the container to create
        :param public: bool, set container as public
        :param atomic_action: bool, enable create container to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to put_container

        :returns: container name
        """
        if public:
            kwargs.setdefault("headers", {})
            kwargs["headers"].setdefault("X-Container-Read", ".r:*,.rlistings")

        if container_name is None:
            container_name = self._generate_random_name(
                prefix="rally_container_")

        if atomic_action:
            with atomic.ActionTimer(self, "swift.create_container"):
                self.clients("swift").put_container(container_name, **kwargs)
        else:
            self.clients("swift").put_container(container_name, **kwargs)
        return container_name

    def _delete_container(self, container_name, atomic_action=True, **kwargs):
        """Delete a container with given name.

        :param container_name: str, name of the container to delete
        :param atomic_action: bool, enable delete container to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to delete_container
        """
        if atomic_action:
            with atomic.ActionTimer(self, "swift.delete_container"):
                self.clients("swift").delete_container(container_name,
                                                       **kwargs)
        else:
            self.clients("swift").delete_container(container_name, **kwargs)

    def _list_objects(self, container_name, full_listing=True,
                      atomic_action=True, **kwargs):
        """Return objects inside container.

        :param container_name: str, name of the container to make the list
                               objects operation against
        :param full_listing: bool, enable unlimit number of listing returned
        :param atomic_action: bool, enable list objects to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to get_container

        :returns: tuple, (dict of response headers, a list of objects)
        """
        if atomic_action:
            with atomic.ActionTimer(self, "swift.list_objects"):
                return self.clients("swift").get_container(
                    container_name, full_listing=full_listing,
                    **kwargs)

        return self.clients("swift").get_container(container_name,
                                                   full_listing=full_listing,
                                                   **kwargs)

    def _upload_object(self, container_name, content, object_name=None,
                       atomic_action=True, **kwargs):
        """Upload content to a given container.

        :param container_name: str, name of the container to upload object to
        :param content: file stream, content to upload
        :param object_name: str, name of the object to upload
        :param atomic_action: bool, enable upload object to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to put_object

        :returns: tuple, (etag and object name)
        """
        if object_name is None:
            object_name = self._generate_random_name(prefix="rally_object_")

        if atomic_action:
            with atomic.ActionTimer(self, "swift.upload_object"):
                return (self.clients("swift").put_object(container_name,
                                                         object_name, content,
                                                         **kwargs),
                        object_name)

        return (self.clients("swift").put_object(container_name, object_name,
                                                 content, **kwargs),
                object_name)

    def _download_object(self, container_name, object_name, atomic_action=True,
                         **kwargs):
        """Download object from container.

        :param container_name: str, name of the container to download object
                               from
        :param object_name: str, name of the object to download
        :param atomic_action: bool, enable download object to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to get_object

        :returns: tuple, (dict of response headers, the object's contents)
        """
        if atomic_action:
            with atomic.ActionTimer(self, "swift.download_object"):
                return self.clients("swift").get_object(container_name,
                                                        object_name, **kwargs)

        return self.clients("swift").get_object(container_name, object_name,
                                                **kwargs)

    def _delete_object(self, container_name, object_name, atomic_action=True,
                       **kwargs):
        """Delete object from container.

        :param container_name: str, name of the container to delete object from
        :param object_name: str, name of the object to delete
        :param atomic_action: bool, enable delete object to be tracked as an
                              atomic action
        :param kwargs: dict, other optional parameters to delete_object
        """
        if atomic_action:
            with atomic.ActionTimer(self, "swift.delete_object"):
                self.clients("swift").delete_object(container_name,
                                                    object_name, **kwargs)
        else:
            self.clients("swift").delete_object(container_name, object_name,
                                                **kwargs)
