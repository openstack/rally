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
from rally.plugins.openstack import osclients

LOG = logging.getLogger(__file__)


class OpenStackCredential(object):
    """Credential for OpenStack."""

    def __init__(self, auth_url, username, password, tenant_name=None,
                 project_name=None,
                 permission=consts.EndpointPermission.USER,
                 region_name=None, endpoint_type=None,
                 domain_name=None, endpoint=None, user_domain_name=None,
                 project_domain_name=None,
                 https_insecure=False, https_cacert=None,
                 profiler_hmac_key=None, profiler_conn_str=None):
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
        self.profiler_conn_str = profiler_conn_str

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
                "profiler_hmac_key": self.profiler_hmac_key,
                "profiler_conn_str": self.profiler_conn_str}

    def verify_connection(self):
        if self.permission == consts.EndpointPermission.ADMIN:
            self.clients().verified_keystone()
        else:
            self.clients().keystone()

    def list_services(self):
        return sorted([{"type": stype, "name": sname}
                       for stype, sname in self.clients().services().items()],
                      key=lambda s: s["name"])

    @classmethod
    def get_validation_context(cls):
        return {"users@openstack": {}}

    def clients(self, api_info=None):
        return osclients.Clients(self, api_info=api_info,
                                 cache=self._clients_cache)
