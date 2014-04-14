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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.keystone import utils as kutils
from rally.benchmark import validation as valid


class KeystoneBasic(kutils.KeystoneScenario):

    @base.scenario(admin_only=True, context={"cleanup": []})
    def create_user(self, name_length=10, **kwargs):
        self._user_create(name_length=name_length, **kwargs)

    @base.scenario(admin_only=True, context={"cleanup": []})
    def create_delete_user(self, name_length=10, **kwargs):
        user = self._user_create(name_length=name_length, **kwargs)
        self._resource_delete(user)

    @base.scenario(admin_only=True, context={"cleanup": []})
    def create_tenant(self, name_length=10, **kwargs):
        self._tenant_create(name_length=name_length, **kwargs)

    @base.scenario(admin_only=True, context={"cleanup": []})
    @valid.add_validator(valid.required_parameters(['users_per_tenant']))
    def create_tenant_with_users(self, users_per_tenant, name_length=10,
                                 **kwargs):
        tenant = self._tenant_create(name_length=name_length, **kwargs)
        self._users_create(tenant, users_per_tenant=users_per_tenant,
                           name_length=name_length)

    @base.scenario(admin_only=True, context={"cleanup": []})
    def create_and_list_users(self, name_length=10, **kwargs):
        self._user_create(name_length=name_length, **kwargs)
        self._list_users()

    @base.scenario(admin_only=True, context={"cleanup": []})
    def create_and_list_tenants(self, name_length=10, **kwargs):
        self._tenant_create(name_length=name_length, **kwargs)
        self._list_tenants()
