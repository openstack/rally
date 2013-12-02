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

import urlparse

from cinderclient import client as cinder
import glanceclient as glance
from keystoneclient.v2_0 import client as keystone
from novaclient import client as nova


class Clients(object):
    """This class simplify and unify work with openstack python clients."""

    def __init__(self, username, password, tenant_name, auth_url):
        self.kw = {'username': username, 'password': password,
                   'tenant_name': tenant_name, 'auth_url': auth_url}
        self.cache = {}

    def get_keystone_client(self):
        """Return keystone client."""
        if "keystone" in self.cache:
            return self.cache["keystone"]

        new_kw = {"endpoint": self._change_port(self.kw["auth_url"], "35357")}
        kw = dict(self.kw.items() + new_kw.items())
        client = keystone.Client(**kw)
        client.authenticate()

        self.cache["keystone"] = client
        return client

    def get_nova_client(self, version='2'):
        """Returns nova client."""
        if "nova" in self.cache:
            return self.cache["nova"]

        client = nova.Client(version,
                             self.kw['username'],
                             self.kw['password'],
                             self.kw['tenant_name'],
                             auth_url=self.kw['auth_url'],
                             service_type='compute')

        self.cache["nova"] = client
        return client

    def get_glance_client(self, version='1'):
        """Returns glance client."""
        if "glance" in self.cache:
            return self.cache["glance"]

        kc = self.get_keystone_client()
        endpoint = kc.service_catalog.get_endpoints()['image'][0]
        client = glance.Client(version,
                               endpoint=endpoint['publicURL'],
                               token=kc.auth_token)

        self.cache["glance"] = client
        return client

    def get_cinder_client(self, version='1'):
        """Returns cinder client."""
        if "cinder" in self.cache:
            return self.cache["cinder"]

        client = cinder.Client(version,
                               self.kw['username'],
                               self.kw['password'],
                               self.kw['tenant_name'],
                               auth_url=self.kw['auth_url'],
                               service_type='volume')

        self.cache["cinder"] = client
        return client

    def _change_port(self, url, new_port):
        """Change the port of a given url.

        :param url: URL string
        :param new_port: The new port

        :returns: URL string
        """
        url_obj = urlparse.urlparse(url)
        new_url = "%(scheme)s://%(hostname)s:%(port)s%(path)s" % {
                    "scheme": url_obj.scheme, "hostname": url_obj.hostname,
                    "port": new_port, "path": url_obj.path}
        return new_url
