# Copyright 2014: Dassault Systemes
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

from rally.benchmark import context
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import osclients
from rally.plugins.openstack.context.quotas import cinder_quotas
from rally.plugins.openstack.context.quotas import designate_quotas
from rally.plugins.openstack.context.quotas import manila_quotas
from rally.plugins.openstack.context.quotas import neutron_quotas
from rally.plugins.openstack.context.quotas import nova_quotas


LOG = logging.getLogger(__name__)


@context.context(name="quotas", order=300)
class Quotas(context.Context):
    """Context class for updating benchmarks' tenants quotas."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "nova": nova_quotas.NovaQuotas.QUOTAS_SCHEMA,
            "cinder": cinder_quotas.CinderQuotas.QUOTAS_SCHEMA,
            "manila": manila_quotas.ManilaQuotas.QUOTAS_SCHEMA,
            "designate": designate_quotas.DesignateQuotas.QUOTAS_SCHEMA,
            "neutron": neutron_quotas.NeutronQuotas.QUOTAS_SCHEMA
        }
    }

    def __init__(self, ctx):
        super(Quotas, self).__init__(ctx)
        self.clients = osclients.Clients(self.context["admin"]["endpoint"])

        self.manager = {
            "nova": nova_quotas.NovaQuotas(self.clients),
            "cinder": cinder_quotas.CinderQuotas(self.clients),
            "manila": manila_quotas.ManilaQuotas(self.clients),
            "designate": designate_quotas.DesignateQuotas(self.clients),
            "neutron": neutron_quotas.NeutronQuotas(self.clients)
        }

    def _service_has_quotas(self, service):
        return len(self.config.get(service, {})) > 0

    @utils.log_task_wrapper(LOG.info, _("Enter context: `quotas`"))
    def setup(self):
        for tenant_id in self.context["tenants"]:
            for service in self.manager:
                if self._service_has_quotas(service):
                    self.manager[service].update(tenant_id,
                                                 **self.config[service])

    @utils.log_task_wrapper(LOG.info, _("Exit context: `quotas`"))
    def cleanup(self):
        for service in self.manager:
            if self._service_has_quotas(service):
                for tenant_id in self.context["tenants"]:
                    try:
                        self.manager[service].delete(tenant_id)
                    except Exception as e:
                        LOG.warning("Failed to remove quotas for tenant "
                                    "%(tenant_id)s in service %(service)s "
                                    "\n reason: %(exc)s"
                                    % {"tenant_id": tenant_id,
                                       "service": service, "exc": e})
