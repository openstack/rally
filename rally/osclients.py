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

from cinderclient import client as cinder
import glanceclient as glance
from keystoneclient.v2_0 import client as keystone
from novaclient import client as nova


class Clients(object):
    """This class simplify and unify work with openstack python clients."""

    def __init__(self, username, password, tenant_name, auth_url):
        self.kw = {'username': username, 'password': password,
                   'tenant_name': tenant_name, 'auth_url': auth_url}

    def get_keystone_client(self):
        """Return keystone client."""
        return keystone.Client(**self.kw)

    def get_nova_client(self, version='2'):
        """Returns nova client."""
        return nova.Client(version,
                           self.kw['username'],
                           self.kw['password'],
                           self.kw['tenant_name'],
                           auth_url=self.kw['auth_url'],
                           service_type='compute')

    def get_glance_client(self, version='1'):
        """Returns glance client."""
        kc = self.get_keystone_client()
        endpoint = kc.service_catalog.get_endpoints()['image'][0]
        return glance.Client(version,
                             endpoint=endpoint['publicURL'],
                             token=kc.auth_token)

    def get_cinder_client(self, version='1'):
        """Returns cinder client."""
        return cinder.Client(version,
                             self.kw['username'],
                             self.kw['password'],
                             self.kw['tenant_name'],
                             auth_url=self.kw['auth_url'],
                             service_type='volume')
