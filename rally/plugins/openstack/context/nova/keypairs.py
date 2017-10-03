# Copyright 2014: Rackspace UK
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

from rally.common import validation
from rally.plugins.openstack.cleanup import manager as resource_manager
from rally.plugins.openstack import osclients
from rally.task import context


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="keypair", platform="openstack", order=310)
class Keypair(context.Context):
    """Create Nova KeyPair for each user."""

    # NOTE(andreykurilin): "type" != "null", since we need to support backward
    #   compatibility(previously empty dict was valid) and I hope in near
    #   future, we will extend this context to accept keys.
    CONFIG_SCHEMA = {"type": "object",
                     "additionalProperties": False}

    def _generate_keypair(self, credential):
        nova_client = osclients.Clients(credential).nova()
        # NOTE(hughsaunders): If keypair exists, it should re-generate name.

        keypairs = nova_client.keypairs.list()
        keypair_names = [keypair.name for keypair in keypairs]
        while True:
            keypair_name = self.generate_random_name()
            if keypair_name not in keypair_names:
                break

        keypair = nova_client.keypairs.create(keypair_name)
        return {"private": keypair.private_key,
                "public": keypair.public_key,
                "name": keypair_name,
                "id": keypair.id}

    def setup(self):
        for user in self.context["users"]:
            user["keypair"] = self._generate_keypair(user["credential"])

    def cleanup(self):
        resource_manager.cleanup(names=["nova.keypairs"],
                                 users=self.context.get("users", []),
                                 superclass=self.__class__,
                                 task_id=self.get_owner_id())
