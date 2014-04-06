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
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils


LOG = logging.getLogger(__name__)


class Keypair(base.Context):
    __ctx_name__ = "keypair"
    __ctx_order__ = 300
    __ctx_hidden__ = True

    KEYPAIR_NAME = "rally_ssh_key"

    def _get_nova_client(self, endpoint):
        return osclients.Clients(endpoint).nova()

    def _keypair_safe_remove(self, nova):
        try:
            nova.keypairs.delete(self.KEYPAIR_NAME)
        except novaclient.exceptions.NotFound:
            pass

    def _generate_keypair(self, endpoint):
        nova = self._get_nova_client(endpoint)

        # NOTE(hughsaunders): If keypair exists, it must be deleted as we can't
        # retrieve the private key
        self._keypair_safe_remove(nova)

        keypair = nova.keypairs.create(self.KEYPAIR_NAME)
        return {"private": keypair.private_key,
                "public": keypair.public_key}

    @utils.log_task_wrapper(LOG.info, _("Enter context: `keypair`"))
    def setup(self):
        for user in self.context["users"]:
            keypair = self._generate_keypair(user["endpoint"])
            user["keypair"] = keypair

    @utils.log_task_wrapper(LOG.info, _("Exit context: `keypair`"))
    def cleanup(self):
        for user in self.context["users"]:
            endpoint = user['endpoint']
            try:
                nova = self._get_nova_client(endpoint)
                self._keypair_safe_remove(nova)
            except Exception as e:
                LOG.warning("Unable to delete keypair: %(kpname)s for user "
                            "%(tenant)s/%(user)s: %(message)s"
                            % {'kpname': self.KEYPAIR_NAME,
                               'tenant': endpoint.tenant_name,
                               'user': endpoint.username,
                               'message': e.message})
