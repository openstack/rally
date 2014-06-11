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

from rally.benchmark.context import base
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils


LOG = logging.getLogger(__name__)


class NovaQuotas(object):
    """Management of Nova quotas."""

    QUOTAS_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "instances": {
                "type": "integer",
                "minimum": -1
            },
            "cores": {
                "type": "integer",
                "minimum": -1
            },
            "ram": {
                "type": "integer",
                "minimum": -1
            },
            "floating_ips": {
                "type": "integer",
                "minimum": -1
            },
            "fixed_ips": {
                "type": "integer",
                "minimum": -1
            },
            "metadata_items": {
                "type": "integer",
                "minimum": -1
            },
            "injected_files": {
                "type": "integer",
                "minimum": -1
            },
            "injected_file_content_bytes": {
                "type": "integer",
                "minimum": -1
            },
            "injected_file_path_bytes": {
                "type": "integer",
                "minimum": -1
            },
            "key_pairs": {
                "type": "integer",
                "minimum": -1
            },
            "security_groups": {
                "type": "integer",
                "minimum": -1
            },
            "security_group_rules": {
                "type": "integer",
                "minimum": -1
            }
        }
    }

    def __init__(self, clients):
        self.clients = clients

    def update(self, tenant_id, **kwargs):
        self.clients.nova().quotas.update(tenant_id, **kwargs)

    def delete(self, tenant_id):
        # Reset quotas to defaults and tag database objects as deleted
        self.clients.nova().quotas.delete(tenant_id)


class CinderQuotas(object):
    """Management of Cinder quotas."""

    QUOTAS_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "gigabytes": {
                "type": "integer",
                "minimum": -1
            },
            "snapshots": {
                "type": "integer",
                "minimum": -1
            },
            "volumes": {
                "type": "integer",
                "minimum": -1
            }
        }
    }

    def __init__(self, clients):
        self.clients = clients

    def update(self, tenant_id, **kwargs):
        self.clients.cinder().quotas.update(tenant_id, **kwargs)

    def delete(self, tenant_id):
        # Currently, no method to delete quotas available in cinder client:
        # Will be added with https://review.openstack.org/#/c/74841/
        pass


class NeutronQuotas(object):
    """Management of Neutron quotas."""

    QUOTAS_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "network": {
                "type": "integer",
                "minimum": -1
            },
            "subnet": {
                "type": "integer",
                "minimum": -1
            },
            "port": {
                "type": "integer",
                "minimum": -1
            },
            "router": {
                "type": "integer",
                "minimum": -1
            },
            "floatingip": {
                "type": "integer",
                "minimum": -1
            },
            "security_group": {
                "type": "integer",
                "minimum": -1
            },
            "security_group_rule": {
                "type": "integer",
                "minimum": -1
            }
        }
    }

    def __init__(self, clients):
        self.clients = clients

    def update(self, tenant_id, **kwargs):
        body = {"quota": kwargs}
        self.clients.neutron().update_quota(tenant_id, body=body)

    def delete(self, tenant_id):
        # Reset quotas to defaults and tag database objects as deleted
        self.clients.neutron().delete_quota(tenant_id)


class Quotas(base.Context):
    """Context class for updating benchmarks' tenants quotas."""

    __ctx_name__ = "quotas"
    __ctx_order__ = 210
    __ctx_hidden__ = False

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": utils.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "nova": NovaQuotas.QUOTAS_SCHEMA,
            "cinder": CinderQuotas.QUOTAS_SCHEMA,
            "neutron": NeutronQuotas.QUOTAS_SCHEMA
        }
    }

    def __init__(self, context):
        super(Quotas, self).__init__(context)
        self.clients = osclients.Clients(context["admin"]["endpoint"])

        self.manager = {
            "nova": NovaQuotas(self.clients),
            "cinder": CinderQuotas(self.clients),
            "neutron": NeutronQuotas(self.clients)
        }

    def _service_has_quotas(self, service):
        return len(self.config.get(service, {})) > 0

    @utils.log_task_wrapper(LOG.info, _("Enter context: `quotas`"))
    def setup(self):
        for tenant in self.context["tenants"]:
            for service in self.manager:
                if self._service_has_quotas(service):
                    self.manager[service].update(tenant["id"],
                                                 **self.config[service])

    @utils.log_task_wrapper(LOG.info, _("Exit context: `quotas`"))
    def cleanup(self):
        for service in self.manager:
            if self._service_has_quotas(service):
                for tenant in self.context["tenants"]:
                    try:
                        self.manager[service].delete(tenant["id"])
                    except Exception as e:
                        LOG.warning("Failed to remove quotas for tenant "
                                    "%(tenant_id)s in service %(service)s "
                                    "\n reason: %(exc)s"
                                    % {"tenant_id": tenant["id"],
                                       "service": service, "exc": e})
