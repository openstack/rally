# Copyright 2014 Red Hat, Inc. <http://www.redhat.com>
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

from rally.benchmark import base
from rally import osclients


class Authenticate(base.Scenario):
    """This class should contain authentication mechanism for different
    types of clients like Keystone.
    """
    def keystone(self, **kwargs):
        keystone_cl = self.clients("endpoint")
        cl_username = keystone_cl["username"]
        cl_password = keystone_cl["password"]
        cl_tenant = keystone_cl["tenant_name"]
        cl_auth_url = keystone_cl["auth_url"]
        cl = osclients.Clients(cl_username, cl_password, cl_tenant,
                               cl_auth_url)
        cl.get_keystone_client()
