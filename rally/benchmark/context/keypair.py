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

import novaclient.exceptions

from rally.benchmark.context import base
from rally.benchmark.context.cleanup import manager as resource_manager
from rally.i18n import _
from rally import log as logging
from rally import osclients
from rally import utils


LOG = logging.getLogger(__name__)


@base.context(name="keypair", order=310)
class Keypair(base.Context):
    KEYPAIR_NAME = "rally_ssh_key"

    def _generate_keypair(self, endpoint):
        nova_client = osclients.Clients(endpoint).nova()

        # NOTE(hughsaunders): If keypair exists, it must be deleted as we can't
        # retrieve the private key
        try:
            nova_client.keypairs.delete(self.KEYPAIR_NAME)
        except novaclient.exceptions.NotFound:
            pass

        keypair = nova_client.keypairs.create(self.KEYPAIR_NAME)
        return {"private": keypair.private_key,
                "public": keypair.public_key}

    @utils.log_task_wrapper(LOG.info, _("Enter context: `keypair`"))
    def setup(self):
        for user in self.context["users"]:
            keypair = self._generate_keypair(user["endpoint"])
            user["keypair"] = keypair

    @utils.log_task_wrapper(LOG.info, _("Exit context: `keypair`"))
    def cleanup(self):
        # TODO(boris-42): Delete only resources created by this context
        resource_manager.cleanup(names=["nova.keypairs"],
                                 users=self.context.get("users", []))
