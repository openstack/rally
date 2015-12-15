# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from rally.common.i18n import _
from rally.common import logging
from rally.common import utils
from rally import consts
from rally import osclients
from rally.plugins.openstack.wrappers import network as network_wrapper
from rally.task import context


LOG = logging.getLogger(__name__)


@context.configure(name="existing_network", order=349)
class ExistingNetwork(context.Context):
    """This context supports using existing networks in Rally.

    This context should be used on a deployment with existing users.
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False
    }

    @logging.log_task_wrapper(LOG.info, _("Enter context: `existing_network`"))
    def setup(self):
        for user, tenant_id in utils.iterate_per_tenants(
                self.context.get("users", [])):
            net_wrapper = network_wrapper.wrap(
                osclients.Clients(user["credential"]), self,
                config=self.config)
            self.context["tenants"][tenant_id]["networks"] = (
                net_wrapper.list_networks())

    @logging.log_task_wrapper(LOG.info, _("Exit context: `existing_network`"))
    def cleanup(self):
        """Networks were not created by Rally, so nothing to do."""
