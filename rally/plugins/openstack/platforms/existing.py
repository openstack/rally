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

import copy
import sys

from rally.common import logging
from rally.env import platform
from rally.plugins.openstack import osclients


LOG = logging.getLogger(__name__)


@platform.configure(name="existing", platform="openstack")
class OpenStack(platform.Platform):
    """Default plugin for OpenStack platform

    It may be used to test any existing OpenStack API compatible cloud.
    """
    CONFIG_SCHEMA = {
        "type": "object",
        "definitions": {
            "user": {
                "type": "object",
                "oneOf": [
                    {
                        "description": "Keystone V2.0",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "tenant_name": {"type": "string"},
                        },
                        "required": ["username", "password", "tenant_name"],
                        "additionalProperties": False
                    },
                    {
                        "description": "Keystone V3.0",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string"},
                            "project_name": {"type": "string"},
                            "domain_name": {"type": "string"},
                            "user_domain_name": {"type": "string"},
                            "project_domain_name": {"type": "string"},
                        },
                        "required": ["username", "password", "project_name"],
                        "additionalProperties": False
                    }
                ],
            }
        },
        "properties": {
            "auth_url": {"type": "string"},
            "region_name": {"type": "string"},
            "endpoint": {"type": ["string", "null"]},
            "endpoint_type": {"enum": ["public", "internal", "admin", None]},
            "https_insecure": {"type": "boolean"},
            "https_cacert": {"type": "string"},
            "profiler_hmac_key": {"type": ["string", "null"]},
            "profiler_conn_str": {"type": ["string", "null"]},
            "admin": {"$ref": "#/definitions/user"},
            "users": {
                "type": "array",
                "items": {"$ref": "#/definitions/user"},
                "minItems": 1
            }
        },
        "anyOf": [
            {
                "description": "The case when the admin is specified and the "
                               "users can be created via 'users@openstack' "
                               "context or 'existing_users' will be used.",
                "required": ["admin", "auth_url"]},
            {
                "description": "The case when the only existing users are "
                               "specified.",
                "required": ["users", "auth_url"]}
        ],
        "additionalProperties": False
    }

    _DEFAULTS = {
        "region_name": None,
        "endpoint_type": None,
        "domain_name": None,
        "user_domain_name": None,
        "project_domain_name": None,
        "https_insecure": False,
        "https_cacert": None
    }

    def create(self):
        """Converts creds of real OpenStack to internal presentation."""
        new_data = copy.deepcopy(self.spec)
        if "endpoint" in new_data:
            LOG.warning("endpoint is deprecated and not used.")
            del new_data["endpoint"]
        admin = new_data.pop("admin", None)
        users = new_data.pop("users", [])

        if admin:
            if "project_name" in admin:
                admin["tenant_name"] = admin.pop("project_name")
            admin.update(new_data)
            for k, v in self._DEFAULTS.items():
                admin.setdefault(k, v)
        for user in users:
            if "project_name" in user:
                user["tenant_name"] = user.pop("project_name")
            user.update(new_data)
            for k, v in self._DEFAULTS.items():
                user.setdefault(k, v)
        return {"admin": admin, "users": users}, {}

    def destroy(self):
        # NOTE(boris-42): No action need to be performed.
        pass

    def cleanup(self, task_uuid=None):
        return {
            "message": "Coming soon!",
            "discovered": 0,
            "deleted": 0,
            "failed": 0,
            "resources": {},
            "errors": []
        }

    def check_health(self):
        """Check whatever platform is alive."""
        if self.platform_data["admin"]:
            try:
                osclients.Clients(
                    self.platform_data["admin"]).verified_keystone()
            except Exception:
                return {
                    "available": False,
                    "message": ("Bad admin creds: %s"
                                % self.platform_data["admin"]),
                    "traceback": list(sys.exc_info())
                }

        for user in self.platform_data["users"]:
            try:
                osclients.Clients(user).keystone()
            except Exception:
                return {
                    "available": False,
                    "message": ("Bad user creds: %s" % user),
                    "traceback": list(sys.exc_info())
                }

        return {"available": True}

    def info(self):
        """Return information about cloud as dict."""
        active_user = (self.platform_data["admin"] or
                       self.platform_data["users"][0])
        return {
            "info": {
                "services": osclients.Clients(active_user).list_services()
            }
        }

    def _get_validation_context(self):
        return {"users@openstack": {}}
