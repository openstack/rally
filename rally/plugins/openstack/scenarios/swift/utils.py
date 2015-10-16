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

    @atomic.optional_action_timer("swift.create_container")
    def _create_container(self, public=False, **kwargs):
        """Create a new container.

        :param public: bool, set container as public
        :param atomic_action: bool, enable create container to be
                              tracked as an atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        :param kwargs: dict, other optional parameters to put_container

        :returns: container name
        """
        if public:
            kwargs.setdefault("headers", {})
            kwargs["headers"].setdefault("X-Container-Read", ".r:*,.rlistings")

        container_name = self.generate_random_name()

        self.clients("swift").put_container(container_name, **kwargs)
        return container_name

    @atomic.optional_action_timer("swift.delete_container")
    def _delete_container(self, container_name, **kwargs):
        """Delete a container with given name.

        :param container_name: str, name of the container to delete
        :param atomic_action: bool, enable delete container to be
                              tracked as an atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        :param kwargs: dict, other optional parameters to delete_container
        """
        self.clients("swift").delete_container(container_name, **kwargs)

    @atomic.optional_action_timer("swift.list_objects")
    def _list_objects(self, container_name, full_listing=True, **kwargs):
        """Return objects inside container.

        :param container_name: str, name of the container to make the list
                               objects operation against
        :param full_listing: bool, enable unlimit number of listing returned
        :param atomic_action: bool, enable list objects to be tracked
                              as an atomic action. added and handled
                              by the optional_action_timer() decorator
        :param kwargs: dict, other optional parameters to get_container

        :returns: tuple, (dict of response headers, a list of objects)
        """
        return self.clients("swift").get_container(container_name,
                                                   full_listing=full_listing,
                                                   **kwargs)

    @atomic.optional_action_timer("swift.upload_object")
    def _upload_object(self, container_name, content, **kwargs):
        """Upload content to a given container.

        :param container_name: str, name of the container to upload object to
        :param content: file stream, content to upload
        :param atomic_action: bool, enable upload object to be tracked
                              as an atomic action. added and handled
                              by the optional_action_timer() decorator
        :param kwargs: dict, other optional parameters to put_object

        :returns: tuple, (etag and object name)
        """
        object_name = self.generate_random_name()

        return (self.clients("swift").put_object(container_name, object_name,
                                                 content, **kwargs),
                object_name)

    @atomic.optional_action_timer("swift.download_object")
    def _download_object(self, container_name, object_name, **kwargs):
        """Download object from container.

        :param container_name: str, name of the container to download object
                               from
        :param object_name: str, name of the object to download
        :param atomic_action: bool, enable download object to be
                              tracked as an atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        :param kwargs: dict, other optional parameters to get_object

        :returns: tuple, (dict of response headers, the object's contents)
        """
        return self.clients("swift").get_object(container_name, object_name,
                                                **kwargs)

    @atomic.optional_action_timer("swift.delete_object")
    def _delete_object(self, container_name, object_name, **kwargs):
        """Delete object from container.

        :param container_name: str, name of the container to delete object from
        :param object_name: str, name of the object to delete
        :param atomic_action: bool, enable delete object to be tracked
                              as an atomic action. added and handled
                              by the optional_action_timer() decorator
        :param kwargs: dict, other optional parameters to delete_object
        """
        self.clients("swift").delete_object(container_name, object_name,
                                            **kwargs)
