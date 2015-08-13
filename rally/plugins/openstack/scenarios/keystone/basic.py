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

from rally.common import utils
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.keystone import utils as kutils
from rally.task import validation


class KeystoneBasic(kutils.KeystoneScenario):
    """Basic benchmark scenarios for Keystone."""

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_user(self, name_length=10, **kwargs):
        """Create a keystone user with random name.

        :param name_length: length of the random part of user name
        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        self._user_create(name_length=name_length, **kwargs)

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_delete_user(self, name_length=10, **kwargs):
        """Create a keystone user with random name and then delete it.

        :param name_length: length of the random part of user name
        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        user = self._user_create(name_length=name_length, **kwargs)
        self._resource_delete(user)

    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_user_set_enabled_and_delete(self, enabled=True, **kwargs):
        """Create a keystone user, enable or disable it, and delete it.

        :param enabled: Initial state of user 'enabled' flag. The user
                        will be created with 'enabled' set to this
                        value, and then it will be toggled.
        :param kwargs: Other optional parameters to create user.
        """
        user = self._user_create(enabled=enabled, **kwargs)
        self._update_user_enabled(user, not enabled)
        self._resource_delete(user)

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_tenant(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name.

        :param name_length: length of the random part of tenant name
        :param kwargs: Other optional parameters
        """
        self._tenant_create(name_length=name_length, **kwargs)

    @validation.number("name_length", minval=10)
    @validation.number("users_per_tenant", minval=1)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_tenant_with_users(self, users_per_tenant, name_length=10,
                                 **kwargs):
        """Create a keystone tenant and several users belonging to it.

        :param name_length: length of the random part of tenant/user name
        :param users_per_tenant: number of users to create for the tenant
        :param kwargs: Other optional parameters for tenant creation
        :returns: keystone tenant instance
        """
        tenant = self._tenant_create(name_length=name_length, **kwargs)
        self._users_create(tenant, users_per_tenant=users_per_tenant,
                           name_length=name_length)

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_list_users(self, name_length=10, **kwargs):
        """Create a keystone user with random name and list all users.

        :param name_length: length of the random part of user name
        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        self._user_create(name_length=name_length, **kwargs)
        self._list_users()

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_list_tenants(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name and list all tenants.

        :param name_length: length of the random part of tenant name
        :param kwargs: Other optional parameters
        """
        self._tenant_create(name_length=name_length, **kwargs)
        self._list_tenants()

    @validation.required_openstack(admin=True, users=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def add_and_remove_user_role(self):
        """Create a user role add to a user and disassociate."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self._role_create()
        self._role_add(user_id, role, tenant_id)
        self._role_remove(user_id, role, tenant_id)

    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_delete_role(self):
        """Create a user role and delete it."""
        role = self._role_create()
        self._resource_delete(role)

    @validation.required_openstack(admin=True, users=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_add_and_list_user_roles(self):
        """Create user role, add it and list user roles for given user."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self._role_create()
        self._role_add(user_id, role, tenant_id)
        self._list_roles_for_user(user_id, tenant_id)

    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def get_entities(self, service_name="keystone"):
        """Get instance of a tenant, user, role and service by id's.

        An ephemeral tenant, user, and role are each created. By
        default, fetches the 'keystone' service. This can be
        overridden (for instance, to get the 'Identity Service'
        service on older OpenStack), or None can be passed explicitly
        to service_name to create a new service and then query it by
        ID.

        :param service_name: The name of the service to get by ID; or
                             None, to create an ephemeral service and
                             get it by ID.
        """
        tenant = self._tenant_create(name_length=5)
        user = self._user_create(name_length=10)
        role = self._role_create()
        self._get_tenant(tenant.id)
        self._get_user(user.id)
        self._get_role(role.id)
        if service_name is None:
            service = self._service_create()
        else:
            service = self._get_service_by_name(service_name)
        self._get_service(service.id)

    @validation.required_openstack(admin=True)
    @utils.log_deprecated_args(
        "The 'name' argument to create_and_delete_service will be ignored",
        "0.0.5", ["name"])
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_delete_service(self, name=None, service_type=None,
                                  description=None):
        """Create and delete service.

        :param service_type: type of the service
        :param description: description of the service
        """
        service = self._service_create(service_type, description)
        self._delete_service(service.id)

    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_update_and_delete_tenant(self, name_length=10, **kwargs):
        """Create, update and delete tenant.

        :param name_length: length of the random part of tenant name
        :param kwargs: Other optional parameters for tenant creation
        """
        tenant = self._tenant_create(name_length=name_length, **kwargs)
        self._update_tenant(tenant)
        self._resource_delete(tenant)

    @validation.number("password_length", minval=10)
    @validation.number("name_length", minval=10)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_user_update_password(self, name_length=10, password_length=10):
        """Create user and update password for that user.

        :param name_length: length of the user name
        :param password_length: length of the password
        """
        password = self._generate_random_name(length=password_length)
        user = self._user_create(name_length=name_length)
        self._update_user_password(user.id, password)

    @validation.required_openstack(admin=True)
    @utils.log_deprecated_args(
        "The 'name' argument to create_and_list_services will be ignored",
        "0.0.5", ["name"])
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_list_services(self, name=None, service_type=None,
                                 description=None):
        """Create and list services.

        :param service_type: type of the service
        :param description: description of the service
        """
        self._service_create(service_type, description)
        self._list_services()

    @validation.required_openstack(users=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_list_ec2credentials(self):
        """Create and List all keystone ec2-credentials."""
        self._create_ec2credentials(self.context["user"]["id"],
                                    self.context["tenant"]["id"])
        self._list_ec2credentials(self.context["user"]["id"])

    @validation.required_openstack(users=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_delete_ec2credential(self):
        """Create and delete keystone ec2-credential."""
        creds = self._create_ec2credentials(self.context["user"]["id"],
                                            self.context["tenant"]["id"])
        self._delete_ec2credential(self.context["user"]["id"], creds.access)
