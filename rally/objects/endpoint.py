# Copyright 2014: Mirantis Inc.
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

from rally import consts


class Endpoint(object):

    def __init__(self, auth_url, username, password, tenant_name,
                 permission=consts.EndpointPermission.USER,
                 region_name=None):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.tenant_name = tenant_name
        self.permission = permission
        self.region_name = region_name

    def to_dict(self, include_permission=False):
        dct = {"auth_url": self.auth_url, "username": self.username,
               "password": self.password, "tenant_name": self.tenant_name,
               "region_name": self.region_name}
        if include_permission:
            dct["permission"] = self.permission
        return dct
