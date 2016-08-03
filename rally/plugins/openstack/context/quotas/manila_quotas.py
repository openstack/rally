# Copyright 2015 Mirantis Inc.
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


class ManilaQuotas(object):
    """Management of Manila quotas."""

    QUOTAS_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "shares": {
                "type": "integer",
                "minimum": -1
            },
            "gigabytes": {
                "type": "integer",
                "minimum": -1
            },
            "snapshots": {
                "type": "integer",
                "minimum": -1
            },
            "snapshot_gigabytes": {
                "type": "integer",
                "minimum": -1
            },
            "share_networks": {
                "type": "integer",
                "minimum": -1
            }
        }
    }

    def __init__(self, clients):
        self.clients = clients

    def update(self, tenant_id, **kwargs):
        self.clients.manila().quotas.update(tenant_id, **kwargs)

    def delete(self, tenant_id):
        self.clients.manila().quotas.delete(tenant_id)

    def get(self, tenant_id):
        response = self.clients.manila().quotas.get(tenant_id)
        return dict([(k, getattr(response, k))
                     for k in self.QUOTAS_SCHEMA["properties"]])
