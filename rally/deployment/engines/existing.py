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

from rally.common import objects
from rally import consts
from rally.deployment import engine


@engine.configure(name="ExistingCloud")
class ExistingCloud(engine.Engine):
    """Just use an existing OpenStack deployment without deploying anything.

    To use ExistingCloud, you should put credential information to the config:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "auth_url": "http://localhost:5000/v2.0/",
            "region_name": "RegionOne",
            "endpoint_type": "public",
            "admin": {
                "username": "admin",
                "password": "password",
                "tenant_name": "demo"
            },
            "https_insecure": False,
            "https_cacert": "",
        }

    Or, using keystone v3 API endpoint:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "auth_url": "http://localhost:5000/v3/",
            "region_name": "RegionOne",
            "endpoint_type": "public",
            "admin": {
                "username": "admin",
                "password": "admin",
                "user_domain_name": "admin",
                "project_name": "admin",
                "project_domain_name": "admin",
            },
            "https_insecure": False,
            "https_cacert": "",
        }

    To specify extra options use can use special "extra" parameter:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "auth_url": "http://localhost:5000/v2.0/",
            "region_name": "RegionOne",
            "endpoint_type": "public",
            "admin": {
                "username": "admin",
                "password": "password",
                "tenant_name": "demo"
            },
            "https_insecure": False,
            "https_cacert": "",
            "extra": {"some_var": "some_value"}
        }
    """

    CONFIG_SCHEMA = {
        "type": "object",

        "definitions": {
            "user": {
                "type": "object",
                "oneOf": [
                    {
                        # v2.0 authentication
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "tenant_name": {"type": "string"},
                        },
                        "required": ["username", "password", "tenant_name"],
                        "additionalProperties": False
                    },
                    {
                        # Authentication in project scope
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "domain_name": {"type": "string"},
                            "user_domain_name": {"type": "string"},
                            "admin_domain_name": {"type": "string"},
                            "project_name": {"type": "string"},
                            "project_domain_name": {"type": "string"},
                        },
                        "required": ["username", "password", "project_name"],
                        "additionalProperties": False
                    }
                ],
            }
        },

        "properties": {
            "type": {"type": "string"},
            "auth_url": {"type": "string"},
            "region_name": {"type": "string"},
            "endpoint": {"type": ["string", "null"]},
            "endpoint_type": {"enum": [consts.EndpointType.ADMIN,
                                       consts.EndpointType.INTERNAL,
                                       consts.EndpointType.PUBLIC,
                                       None]},
            "https_insecure": {"type": "boolean"},
            "https_cacert": {"type": "string"},
            "admin": {"$ref": "#/definitions/user"},
            "users": {
                "type": "array",
                "items": {"$ref": "#/definitions/user"}
            },
            "extra": {"type": "object", "additionalProperties": True}
        },
        "required": ["type", "auth_url", "admin"],
        "additionalProperties": False
    }

    def _create_credential(self, common, user, permission):
        return objects.Credential(
            common["auth_url"], user["username"], user["password"],
            tenant_name=user.get("project_name", user.get("tenant_name")),
            permission=permission,
            region_name=common.get("region_name"),
            endpoint_type=common.get("endpoint_type"),
            endpoint=common.get("endpoint"),
            domain_name=user.get("domain_name"),
            user_domain_name=user.get("user_domain_name", None),
            admin_domain_name=user.get("admin_domain_name", "Default"),
            project_domain_name=user.get("project_domain_name", None),
            https_insecure=common.get("https_insecure", False),
            https_cacert=common.get("https_cacert")
        )

    def deploy(self):
        permissions = consts.EndpointPermission

        users = [self._create_credential(self.config, user, permissions.USER)
                 for user in self.config.get("users", [])]

        admin = self._create_credential(self.config,
                                        self.config.get("admin"),
                                        permissions.ADMIN)

        return {"admin": admin, "users": users}

    def cleanup(self):
        pass
