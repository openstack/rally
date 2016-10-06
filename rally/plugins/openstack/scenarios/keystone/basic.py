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

from rally.common import logging
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.keystone import utils as kutils
from rally.task import validation


"""Benchmark scenarios for Keystone."""


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user")
class CreateUser(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_user is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        self._user_create(**kwargs)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_delete_user")
class CreateDeleteUser(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_delete_user is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name and then delete it.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        user = self._user_create(**kwargs)
        self._resource_delete(user)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user_set_enabled_and_delete")
class CreateUserSetEnabledAndDelete(kutils.KeystoneScenario):

    def run(self, enabled=True, **kwargs):
        """Create a keystone user, enable or disable it, and delete it.

        :param enabled: Initial state of user 'enabled' flag. The user
                        will be created with 'enabled' set to this
                        value, and then it will be toggled.
        :param kwargs: Other optional parameters to create user.
        """
        user = self._user_create(enabled=enabled, **kwargs)
        self._update_user_enabled(user, not enabled)
        self._resource_delete(user)


@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_tenant")
class CreateTenant(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_tenant is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name.

        :param kwargs: Other optional parameters
        """
        self._tenant_create(**kwargs)


@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.authenticate_user_and_validate_token")
class AuthenticateUserAndValidateToken(kutils.KeystoneScenario):

    def run(self):
        """Authenticate and validate a keystone token."""
        name = self.context["user"]["credential"].username
        password = self.context["user"]["credential"].password
        tenant_id = self.context["tenant"]["id"]
        tenant_name = self.context["tenant"]["name"]

        token = self._authenticate_token(name, password, tenant_id,
                                         tenant_name, atomic_action=False)
        self._token_validate(token.id)


@validation.number("users_per_tenant", minval=1)
@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_tenant_with_users")
class CreateTenantWithUsers(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_tenant_with_users is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, users_per_tenant, name_length=10, **kwargs):
        """Create a keystone tenant and several users belonging to it.

        :param users_per_tenant: number of users to create for the tenant
        :param kwargs: Other optional parameters for tenant creation
        :returns: keystone tenant instance
        """
        tenant = self._tenant_create(**kwargs)
        self._users_create(tenant, users_per_tenant=users_per_tenant)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_users")
class CreateAndListUsers(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_and_list_users is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name and list all users.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        self._user_create(**kwargs)
        self._list_users()


@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_tenants")
class CreateAndListTenants(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_and_list_tenants is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name and list all tenants.

        :param kwargs: Other optional parameters
        """
        self._tenant_create(**kwargs)
        self._list_tenants()


@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.add_and_remove_user_role")
class AddAndRemoveUserRole(kutils.KeystoneScenario):

    def run(self):
        """Create a user role add to a user and disassociate."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self._role_create()
        self._role_add(user_id, role, tenant_id)
        self._role_remove(user_id, role, tenant_id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_role")
class CreateAndDeleteRole(kutils.KeystoneScenario):

    def run(self):
        """Create a user role and delete it."""
        role = self._role_create()
        self._resource_delete(role)


@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_add_and_list_user_roles")
class CreateAddAndListUserRoles(kutils.KeystoneScenario):

    def run(self):
        """Create user role, add it and list user roles for given user."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self._role_create()
        self._role_add(user_id, role, tenant_id)
        self._list_roles_for_user(user_id, tenant_id)


@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.get_entities")
class GetEntities(kutils.KeystoneScenario):

    def run(self, service_name="keystone"):
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
        tenant = self._tenant_create()
        user = self._user_create()
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
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_service")
class CreateAndDeleteService(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name' argument to create_and_delete_service will be ignored",
        "0.0.5", ["name"])
    def run(self, name=None, service_type=None, description=None):
        """Create and delete service.

        :param service_type: type of the service
        :param description: description of the service
        """
        service = self._service_create(service_type, description)
        self._delete_service(service.id)


@validation.required_openstack(admin=True)
@validation.required_api_versions(component="keystone", versions=[2.0])
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_update_and_delete_tenant")
class CreateUpdateAndDeleteTenant(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_update_and_delete_tenant is "
        "ignored", "0.1.2", ["name_length"], once=True)
    def run(self, name_length=None, **kwargs):
        """Create, update and delete tenant.

        :param kwargs: Other optional parameters for tenant creation
        """
        tenant = self._tenant_create(**kwargs)
        self._update_tenant(tenant)
        self._resource_delete(tenant)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user_update_password")
class CreateUserUpdatePassword(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name_length' and 'password_length' arguments to "
        "create_user_update_password are ignored",
        "0.1.2", ["name_length", "password_length"], once=True)
    def run(self, name_length=None, password_length=None):
        """Create user and update password for that user."""
        password = self.generate_random_name()
        user = self._user_create()
        self._update_user_password(user.id, password)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_services")
class CreateAndListServices(kutils.KeystoneScenario):

    @logging.log_deprecated_args(
        "The 'name' argument to create_and_list_services will be ignored",
        "0.0.5", ["name"])
    def run(self, name=None, service_type=None, description=None):
        """Create and list services.

        :param service_type: type of the service
        :param description: description of the service
        """
        self._service_create(service_type, description)
        self._list_services()


@validation.required_openstack(users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_ec2credentials")
class CreateAndListEc2Credentials(kutils.KeystoneScenario):

    def run(self):
        """Create and List all keystone ec2-credentials."""
        self._create_ec2credentials(self.context["user"]["id"],
                                    self.context["tenant"]["id"])
        self._list_ec2credentials(self.context["user"]["id"])


@validation.required_openstack(users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_ec2credential")
class CreateAndDeleteEc2Credential(kutils.KeystoneScenario):

    def run(self):
        """Create and delete keystone ec2-credential."""
        creds = self._create_ec2credentials(self.context["user"]["id"],
                                            self.context["tenant"]["id"])
        self._delete_ec2credential(self.context["user"]["id"], creds.access)
