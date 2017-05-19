# Copyright 2017: Mirantis Inc.
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

from rally.common import logging
from rally import consts
from rally.deployment import credential
from rally import exceptions
from rally import osclients

LOG = logging.getLogger(__file__)


@credential.configure("openstack")
class OpenStackCredential(credential.Credential):
    """Credential for OpenStack."""

    def __init__(self, auth_url, username, password, tenant_name=None,
                 project_name=None,
                 permission=consts.EndpointPermission.USER,
                 region_name=None, endpoint_type=None,
                 domain_name=None, endpoint=None, user_domain_name=None,
                 project_domain_name=None,
                 https_insecure=False, https_cacert=None,
                 profiler_hmac_key=None):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.tenant_name = tenant_name or project_name
        self.permission = permission
        self.region_name = region_name
        self.endpoint_type = endpoint_type
        self.domain_name = domain_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name
        self.endpoint = endpoint
        self.https_insecure = https_insecure
        self.https_cacert = https_cacert
        self.profiler_hmac_key = profiler_hmac_key

        self._clients_cache = {}

    # backward compatibility
    @property
    def insecure(self):
        LOG.warning("Property 'insecure' is deprecated since Rally 0.10.0. "
                    "Use 'https_insecure' instead.")
        return self.https_insecure

    # backward compatibility
    @property
    def cacert(self):
        LOG.warning("Property 'cacert' is deprecated since Rally 0.10.0. "
                    "Use 'https_cacert' instead.")
        return self.https_cacert

    def to_dict(self):
        return {"auth_url": self.auth_url,
                "username": self.username,
                "password": self.password,
                "tenant_name": self.tenant_name,
                "region_name": self.region_name,
                "endpoint_type": self.endpoint_type,
                "domain_name": self.domain_name,
                "endpoint": self.endpoint,
                "https_insecure": self.https_insecure,
                "https_cacert": self.https_cacert,
                "user_domain_name": self.user_domain_name,
                "project_domain_name": self.project_domain_name,
                "permission": self.permission,
                "profiler_hmac_key": self.profiler_hmac_key}

    def verify_connection(self):
        from keystoneclient import exceptions as keystone_exceptions

        try:
            if self.permission == consts.EndpointPermission.ADMIN:
                self.clients().verified_keystone()
            else:
                self.clients().keystone()
        except keystone_exceptions.ConnectionRefused as e:
            if logging.is_debug():
                LOG.exception(e)
            raise exceptions.RallyException("Unable to connect %s." %
                                            self.auth_url)

    def list_services(self):
        return sorted([{"type": stype, "name": sname}
                       for stype, sname in self.clients().services().items()],
                      key=lambda s: s["name"])

    def clients(self, api_info=None):
        return osclients.Clients(self, api_info=api_info,
                                 cache=self._clients_cache)


@credential.configure_builder("openstack")
class OpenStackCredentialBuilder(credential.CredentialBuilder):
    """Builds credentials provided by ExistingCloud config."""

    USER_SCHEMA = {
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
                    "domain_name": {"type": "string"},
                    "user_domain_name": {"type": "string"},
                    "project_name": {"type": "string"},
                    "project_domain_name": {"type": "string"},
                },
                "required": ["username", "password", "project_name"],
                "additionalProperties": False
            }
        ],
    }

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "admin": USER_SCHEMA,
            "users": {"type": "array", "items": USER_SCHEMA},
            "auth_url": {"type": "string"},
            "region_name": {"type": "string"},
            # NOTE(andreykurilin): it looks like we do not use endpoint
            # var at all
            "endpoint": {"type": ["string", "null"]},
            "endpoint_type": {
                "enum": [consts.EndpointType.ADMIN,
                         consts.EndpointType.INTERNAL,
                         consts.EndpointType.PUBLIC,
                         None]},
            "https_insecure": {"type": "boolean"},
            "https_cacert": {"type": "string"},
            "profiler_hmac_key": {"type": ["string", "null"]}
        },
        "required": ["auth_url", "admin"],
        "additionalProperties": False
    }

    def _create_credential(self, common, user, permission):
        cred = OpenStackCredential(
            auth_url=common["auth_url"],
            username=user["username"],
            password=user["password"],
            tenant_name=user.get("project_name", user.get("tenant_name")),
            permission=permission,
            region_name=common.get("region_name"),
            endpoint_type=common.get("endpoint_type"),
            endpoint=common.get("endpoint"),
            domain_name=user.get("domain_name"),
            user_domain_name=user.get("user_domain_name", None),
            project_domain_name=user.get("project_domain_name", None),
            https_insecure=common.get("https_insecure", False),
            https_cacert=common.get("https_cacert"),
            profiler_hmac_key=common.get("profiler_hmac_key"))
        return cred.to_dict()

    def build_credentials(self):
        permissions = consts.EndpointPermission

        users = [self._create_credential(self.config, user, permissions.USER)
                 for user in self.config.get("users", [])]

        admin = self._create_credential(self.config,
                                        self.config.get("admin"),
                                        permissions.ADMIN)

        return {"admin": admin, "users": users}


# NOTE(astudenov): Let's consider moving rally.osclients here
