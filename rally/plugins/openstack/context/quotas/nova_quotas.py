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
            },
            "server_groups": {
                "type": "integer",
                "minimum": -1
            },
            "server_group_members": {
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

    def get(self, tenant_id):
        response = self.clients.nova().quotas.get(tenant_id)
        return dict([(k, getattr(response, k))
                     for k in self.QUOTAS_SCHEMA["properties"]])
