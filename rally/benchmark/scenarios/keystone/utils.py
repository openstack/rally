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


def is_temporary(resource):
    return resource.name.startswith(KeystoneScenario.RESOURCE_NAME_PREFIX)


class KeystoneScenario(base.Scenario):
    RESOURCE_NAME_PREFIX = "rally_keystone_"

    @base.atomic_action_timer('keystone.create_user')
    def _user_create(self, name_length=10, password=None, email=None,
                     **kwargs):
        """Creates keystone user with random name.

        :param name_length: length of generated (random) part of name
        :param **kwargs: Other optional parameters to create users like
                        "tenant_id", "enabled".
        :return: keystone user instance
        """
        name = self._generate_random_name(length=name_length)
        # NOTE(boris-42): password and email parameters are required by
        #                 keystone client v2.0. This should be cleanuped
        #                 when we switch to v3.
        password = password or name
        email = email or (name + "@rally.me")
        return self.admin_clients("keystone").users.create(
                    name, password=password, email=email, **kwargs)

    def _resource_delete(self, resource):
        """"Delete keystone resource."""
        r = "keystone.delete_%s" % resource.__class__.__name__.lower()
        with base.AtomicAction(self, r):
            resource.delete()

    @base.atomic_action_timer('keystone.create_tenant')
    def _tenant_create(self, name_length=10, **kwargs):
        """Creates keystone tenant with random name.

        :param name_length: length of generated (random) part of name
        :param **kwargs: Other optional parameters
        :return: keystone tenant instance
        """
        name = self._generate_random_name(length=name_length)
        return self.admin_clients("keystone").tenants.create(name, **kwargs)

    @base.atomic_action_timer('keystone.create_users')
    def _users_create(self, tenant, users_per_tenant, name_length=10):
        """Adds users to a tenant.

        :param users_per_tenant: number of users in per tenant
        :param name_length: length of generated (random) part of name for user
        """
        for i in range(users_per_tenant):
            name = self._generate_random_name(length=name_length)
            password = name
            email = (name + "@rally.me")
            self.admin_clients("keystone").users.create(
                    name, password=password, email=email, tenant_id=tenant.id)

    @base.atomic_action_timer('keystone.list_users')
    def _list_users(self):
        """list users."""
        return self.admin_clients("keystone").users.list()

    @base.atomic_action_timer('keystone.list_tenants')
    def _list_tenants(self):
        """list tenants."""
        return self.admin_clients("keystone").tenants.list()
