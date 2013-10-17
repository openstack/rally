# Copyright 2013: Mirantis Inc.
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

from rally.benchmark.scenarios.nova import utils


class NovaServers(utils.NovaScenario):

    @classmethod
    def boot_and_delete_server(cls, context, image_id, flavor_id, **kwargs):
        """Tests booting and then deleting an image."""
        server_name = cls._generate_random_name(16)

        server = cls._boot_server(server_name, image_id, flavor_id, **kwargs)
        cls._delete_server(server)

    @classmethod
    def snapshot_server(cls, context, image_id, flavor_id, **kwargs):
        """Tests Nova instance snapshotting."""
        server_name = cls._generate_random_name(16)

        server = cls._boot_server(server_name, image_id, flavor_id, **kwargs)
        image = cls._create_image(server)
        cls._delete_server(server)

        server = cls._boot_server(server_name, image.id, flavor_id, **kwargs)
        cls._delete_server(server)
        cls._delete_image(image)

    @classmethod
    def boot_server(cls, context, image_id, flavor_id, **kwargs):
        """Test VM boot - assumed clean-up is done elsewhere."""
        server_name = cls._generate_random_name(16)
        cls._boot_server(server_name, image_id, flavor_id, **kwargs)
