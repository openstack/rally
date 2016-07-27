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
            },
            "pool": {
                "type": "integer",
                "minimum": -1
            },
            "vip": {
                "type": "integer",
                "minimum": -1
            },
            "health_monitor": {
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

    def get(self, tenant_id):
        return self.clients.neutron().show_quota(tenant_id)["quota"]
