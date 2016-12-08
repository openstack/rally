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

"""
Benchmark scenarios for Keystone.
"""

from rally.common import logging
from rally.plugins.openstack import scenario
from rally.plugins.openstack.services.identity import identity
from rally.task import validation


class KeystoneBasic(scenario.OpenStackScenario):
    """Base class for Keystone scenarios with initialized service object."""

    def __init__(self, context=None, admin_clients=None, clients=None):
        super(KeystoneBasic, self).__init__(context, admin_clients, clients)
        if hasattr(self, "_admin_clients"):
            self.admin_keystone = identity.Identity(
                self._admin_clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())
        if hasattr(self, "_clients"):
            self.keystone = identity.Identity(
                self._clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user")
class CreateUser(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_user is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        self.admin_keystone.create_user(**kwargs)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_delete_user")
class CreateDeleteUser(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_delete_user is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name and then delete it.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        user = self.admin_keystone.create_user(**kwargs)
        self.admin_keystone.delete_user(user.id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user_set_enabled_and_delete")
class CreateUserSetEnabledAndDelete(KeystoneBasic):

    def run(self, enabled=True, **kwargs):
        """Create a keystone user, enable or disable it, and delete it.

        :param enabled: Initial state of user 'enabled' flag. The user
                        will be created with 'enabled' set to this
                        value, and then it will be toggled.
        :param kwargs: Other optional parameters to create user.
        """
        user = self.admin_keystone.create_user(enabled=enabled, **kwargs)
        self.admin_keystone.update_user(user.id, enabled=(not enabled))
        self.admin_keystone.delete_user(user.id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_tenant")
class CreateTenant(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_tenant is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name.

        :param kwargs: Other optional parameters
        """
        self.admin_keystone.create_project(**kwargs)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.authenticate_user_and_validate_token")
class AuthenticateUserAndValidateToken(KeystoneBasic):

    def run(self):
        """Authenticate and validate a keystone token."""
        token = self.admin_keystone.fetch_token()
        self.admin_keystone.validate_token(token)


@validation.number("users_per_tenant", minval=1)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_tenant_with_users")
class CreateTenantWithUsers(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_tenant_with_users is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, users_per_tenant, name_length=10, **kwargs):
        """Create a keystone tenant and several users belonging to it.

        :param users_per_tenant: number of users to create for the tenant
        :param kwargs: Other optional parameters for tenant creation
        :returns: keystone tenant instance
        """
        tenant = self.admin_keystone.create_project(**kwargs)
        self.admin_keystone.create_users(tenant.id,
                                         number_of_users=users_per_tenant)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_users")
class CreateAndListUsers(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_and_list_users is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone user with random name and list all users.

        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """
        kwargs.pop("name", None)
        self.admin_keystone.create_user(**kwargs)
        self.admin_keystone.list_users()


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_tenants")
class CreateAndListTenants(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_and_list_tenants is ignored",
        "0.1.2", ["name_length"], once=True)
    def run(self, name_length=10, **kwargs):
        """Create a keystone tenant with random name and list all tenants.

        :param kwargs: Other optional parameters
        """
        self.admin_keystone.create_project(**kwargs)
        self.admin_keystone.list_projects()


@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.add_and_remove_user_role")
class AddAndRemoveUserRole(KeystoneBasic):

    def run(self):
        """Create a user role add to a user and disassociate."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self.admin_keystone.create_role()
        self.admin_keystone.add_role(role_id=role.id, user_id=user_id,
                                     project_id=tenant_id)
        self.admin_keystone.revoke_role(role.id, user_id=user_id,
                                        project_id=tenant_id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_role")
class CreateAndDeleteRole(KeystoneBasic):

    def run(self):
        """Create a user role and delete it."""
        role = self.admin_keystone.create_role()
        self.admin_keystone.delete_role(role.id)


@validation.required_openstack(admin=True, users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_add_and_list_user_roles")
class CreateAddAndListUserRoles(KeystoneBasic):

    def run(self):
        """Create user role, add it and list user roles for given user."""
        tenant_id = self.context["tenant"]["id"]
        user_id = self.context["user"]["id"]
        role = self.admin_keystone.create_role()
        self.admin_keystone.add_role(user_id=user_id, role_id=role.id,
                                     project_id=tenant_id)
        self.admin_keystone.list_roles(user_id=user_id, project_id=tenant_id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.get_entities")
class GetEntities(KeystoneBasic):

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
        project = self.admin_keystone.create_project()
        user = self.admin_keystone.create_user(project_id=project.id)
        role = self.admin_keystone.create_role()
        self.admin_keystone.get_project(project.id)
        self.admin_keystone.get_user(user.id)
        self.admin_keystone.get_role(role.id)
        if service_name is None:
            service = self.admin_keystone.create_service()
        else:
            service = self.admin_keystone.get_service_by_name(service_name)
        self.admin_keystone.get_service(service.id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_service")
class CreateAndDeleteService(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name' argument to create_and_delete_service will be ignored",
        "0.0.5", ["name"])
    def run(self, name=None, service_type=None, description=None):
        """Create and delete service.

        :param service_type: type of the service
        :param description: description of the service
        """
        service = self.admin_keystone.create_service(service_type=service_type,
                                                     description=description)
        self.admin_keystone.delete_service(service.id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_update_and_delete_tenant")
class CreateUpdateAndDeleteTenant(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' argument to create_update_and_delete_tenant is "
        "ignored", "0.1.2", ["name_length"], once=True)
    def run(self, name_length=None, **kwargs):
        """Create, update and delete tenant.

        :param kwargs: Other optional parameters for tenant creation
        """
        project = self.admin_keystone.create_project(**kwargs)
        new_name = self.generate_random_name()
        new_description = self.generate_random_name()
        self.admin_keystone.update_project(project.id, name=new_name,
                                           description=new_description)
        self.admin_keystone.delete_project(project.id)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_user_update_password")
class CreateUserUpdatePassword(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name_length' and 'password_length' arguments to "
        "create_user_update_password are ignored",
        "0.1.2", ["name_length", "password_length"], once=True)
    def run(self, name_length=None, password_length=None):
        """Create user and update password for that user."""
        user = self.admin_keystone.create_user()
        password = self.generate_random_name()
        self.admin_keystone.update_user(user.id, password=password)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_services")
class CreateAndListServices(KeystoneBasic):

    @logging.log_deprecated_args(
        "The 'name' argument to create_and_list_services will be ignored",
        "0.0.5", ["name"])
    def run(self, name=None, service_type=None, description=None):
        """Create and list services.

        :param service_type: type of the service
        :param description: description of the service
        """
        self.admin_keystone.create_service(service_type=service_type,
                                           description=description)
        self.admin_keystone.list_services()


@validation.required_openstack(users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_list_ec2credentials")
class CreateAndListEc2Credentials(KeystoneBasic):

    def run(self):
        """Create and List all keystone ec2-credentials."""
        self.keystone.create_ec2credentials(
            self.context["user"]["id"],
            project_id=self.context["tenant"]["id"])
        self.keystone.list_ec2credentials(self.context["user"]["id"])


@validation.required_openstack(users=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_delete_ec2credential")
class CreateAndDeleteEc2Credential(KeystoneBasic):

    def run(self):
        """Create and delete keystone ec2-credential."""
        creds = self.keystone.create_ec2credentials(
            self.context["user"]["id"],
            project_id=self.context["tenant"]["id"])
        self.keystone.delete_ec2credential(
            self.context["user"]["id"], access=creds.access)


@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"]},
                    name="KeystoneBasic.create_and_get_role")
class CreateAndGetRole(KeystoneBasic):

    def run(self, **kwargs):
        """Create a user role and get it detailed information.

        :param kwargs: Optional additional arguments for roles creation
        """
        role = self.admin_keystone.create_role(**kwargs)
        self.admin_keystone.get_role(role.id)
