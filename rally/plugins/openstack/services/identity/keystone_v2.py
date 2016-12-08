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

import uuid

from rally.plugins.openstack import service
from rally.plugins.openstack.services.identity import identity
from rally.plugins.openstack.services.identity import keystone_common
from rally.task import atomic


@service.service("keystone", service_type="identity", version="2")
class KeystoneV2Service(service.Service, keystone_common.KeystoneMixin):

    @atomic.action_timer("keystone_v2.create_tenant")
    def create_tenant(self, tenant_name=None):
        tenant_name = tenant_name or self.generate_random_name()
        return self._clients.keystone("2").tenants.create(tenant_name)

    @atomic.action_timer("keystone_v2.update_tenant")
    def update_tenant(self, tenant_id, name=None, enabled=None,
                      description=None):
        """Update tenant name and description.

        :param tenant_id: Id of tenant to update
        :param name: tenant name to be set (if boolean True, random name will
            be set)
        :param enabled: enabled status of project
        :param description: tenant description to be set (if boolean True,
            random description will be set)
        """
        if name is True:
            name = self.generate_random_name()
        if description is True:
            description = self.generate_random_name()
        self._clients.keystone("2").tenants.update(
            tenant_id, name=name, description=description, enabled=enabled)

    @atomic.action_timer("keystone_v2.delete_tenant")
    def delete_tenant(self, tenant_id):
        return self._clients.keystone("2").tenants.delete(tenant_id)

    @atomic.action_timer("keystone_v2.list_tenants")
    def list_tenants(self):
        return self._clients.keystone("2").tenants.list()

    @atomic.action_timer("keystone_v2.get_tenant")
    def get_tenant(self, tenant_id):
        """Get tenant."""
        return self._clients.keystone("2").tenants.get(tenant_id)

    @atomic.action_timer("keystone_v2.create_user")
    def create_user(self, username=None, password=None, email=None,
                    tenant_id=None, enabled=True):
        username = username or self.generate_random_name()
        password = password or str(uuid.uuid4())
        email = email or (username + "@rally.me")
        return self._clients.keystone("2").users.create(name=username,
                                                        password=password,
                                                        email=email,
                                                        tenant_id=tenant_id,
                                                        enabled=enabled)

    @atomic.action_timer("keystone_v2.create_users")
    def create_users(self, tenant_id, number_of_users, user_create_args=None):
        """Create specified amount of users.

        :param tenant_id: Id of tenant
        :param number_of_users: number of users to create
        :param user_create_args: additional user creation arguments
        """
        users = []
        for _i in range(number_of_users):
            users.append(self.create_user(tenant_id=tenant_id,
                                          **(user_create_args or {})))
        return users

    @atomic.action_timer("keystone_v2.update_user")
    def update_user(self, user_id, **kwargs):
        allowed_args = ("name", "email", "enabled")
        restricted = set(kwargs) - set(allowed_args)
        if restricted:
            raise NotImplementedError(
                "Failed to update '%s', since Keystone V2 allows to update "
                "only '%s'." % ("', '".join(restricted),
                                "', '".join(allowed_args)))
        self._clients.keystone("2").users.update(user_id, **kwargs)

    @atomic.action_timer("keystone_v2.update_user_password")
    def update_user_password(self, user_id, password):
        self._clients.keystone("2").users.update_password(user_id,
                                                          password=password)

    @atomic.action_timer("keystone_v2.create_service")
    def create_service(self, name=None, service_type=None, description=None):
        """Creates keystone service.

        :param name: name of service to create
        :param service_type: type of the service
        :param description: description of the service
        :returns: keystone service instance
        """
        name = name or self.generate_random_name()
        service_type = service_type or "rally_test_type"
        description = description or self.generate_random_name()
        return self._clients.keystone("2").services.create(
            name,
            service_type=service_type,
            description=description)

    @atomic.action_timer("keystone_v2.create_role")
    def create_role(self, name=None):
        name = name or self.generate_random_name()
        return self._clients.keystone("2").roles.create(name)

    @atomic.action_timer("keystone_v2.add_role")
    def add_role(self, role_id, user_id, tenant_id):
        self._clients.keystone("2").roles.add_user_role(
            user=user_id, role=role_id, tenant=tenant_id)

    @atomic.action_timer("keystone_v2.list_roles")
    def list_roles(self):
        """List all roles."""
        return self._clients.keystone("2").roles.list()

    @atomic.action_timer("keystone_v2.list_roles_for_user")
    def list_roles_for_user(self, user_id, tenant_id=None):
        return self._clients.keystone("2").roles.roles_for_user(
            user_id, tenant_id)

    @atomic.action_timer("keystone_v2.revoke_role")
    def revoke_role(self, role_id, user_id, tenant_id):
        self._clients.keystone("2").roles.remove_user_role(user=user_id,
                                                           role=role_id,
                                                           tenant=tenant_id)

    @atomic.action_timer("keystone_v2.create_ec2creds")
    def create_ec2credentials(self, user_id, tenant_id):
        """Create ec2credentials.

        :param user_id: User ID for which to create credentials
        :param tenant_id: Tenant ID for which to create credentials

        :returns: Created ec2-credentials object
        """
        return self._clients.keystone("2").ec2.create(user_id,
                                                      tenant_id=tenant_id)


@service.compat_layer(KeystoneV2Service)
class UnifiedKeystoneV2Service(keystone_common.UnifiedKeystoneMixin,
                               identity.Identity):
    """Compatibility layer for Keystone V2."""

    @staticmethod
    def _check_domain(domain_name):
        if domain_name.lower() != "default":
            raise NotImplementedError("Domain functionality not implemented "
                                      "in Keystone v2")

    @staticmethod
    def _unify_tenant(tenant):
        return identity.Project(id=tenant.id, name=tenant.name,
                                domain_id="default")

    @staticmethod
    def _unify_user(user):
        return identity.User(id=user.id, name=user.name,
                             project_id=getattr(user, "tenantId", None),
                             domain_id="default")

    def create_project(self, project_name=None, domain_name="Default"):
        """Creates new project/tenant and return project object.

        :param project_name: Name of project to be created.
        :param domain_name: Restricted for Keystone V2. Should not be set or
            "Default" is expected.
        """
        self._check_domain(domain_name)
        tenant = self._impl.create_tenant(project_name)
        return self._unify_tenant(tenant)

    def update_project(self, project_id, name=None, enabled=None,
                       description=None):
        """Update project name, enabled and description

        :param project_id: Id of project to update
        :param name: project name to be set
        :param enabled: enabled status of project
        :param description: project description to be set
        """
        self._impl.update_tenant(tenant_id=project_id, name=name,
                                 enabled=enabled, description=description)

    def delete_project(self, project_id):
        """Deletes project."""
        return self._impl.delete_tenant(project_id)

    def list_projects(self):
        """List all projects."""
        return [self._unify_tenant(t) for t in self._impl.list_tenants()]

    def get_project(self, project_id):
        """Get project."""
        return self._unify_tenant(self._impl.get_tenant(project_id))

    def create_user(self, username=None, password=None, project_id=None,
                    domain_name="Default", enabled=True,
                    default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param project_id: user's default project
        :param domain_name: Restricted for Keystone V2. Should not be set or
            "Default" is expected.
        :param enabled: whether the user is enabled.
        :param default_role: Restricted for Keystone V2. Should not be set or
            "member" is expected.
        """
        self._check_domain(domain_name)
        user = self._impl.create_user(username=username,
                                      password=password,
                                      tenant_id=project_id,
                                      enabled=enabled)
        return self._unify_user(user)

    def create_users(self, tenant_id, number_of_users, user_create_args=None):
        """Create specified amount of users.

        :param tenant_id: Id of tenant
        :param number_of_users: number of users to create
        :param user_create_args: additional user creation arguments
        """
        if user_create_args and "domain_name" in user_create_args:
            self._check_domain(user_create_args["domain_name"])
        return [self._unify_user(u)
                for u in self._impl.create_users(
                    tenant_id=tenant_id, number_of_users=number_of_users,
                    user_create_args=user_create_args)]

    def list_users(self):
        """List all users."""
        return [self._unify_user(u) for u in self._impl.list_users()]

    def update_user(self, user_id, enabled=None, name=None, email=None,
                    password=None):
        if password is not None:
            self._impl.update_user_password(user_id=user_id, password=password)

        update_args = {}
        if enabled is not None:
            update_args["enabled"] = enabled
        if name is not None:
            update_args["name"] = name
        if email is not None:
            update_args["email"] = email

        if update_args:
            self._impl.update_user(user_id, **update_args)

    def list_services(self):
        """List all services."""
        return [self._unify_service(s) for s in self._impl.list_services()]

    def create_role(self, name=None, domain_name="Default"):
        """Add role to user."""
        self._check_domain(domain_name)
        return self._unify_role(self._impl.create_role(name))

    def add_role(self, role_id, user_id, project_id):
        """Add role to user."""
        self._impl.add_role(role_id=role_id, user_id=user_id,
                            tenant_id=project_id)

    def revoke_role(self, role_id, user_id, project_id):
        """Revokes a role from a user."""
        return self._impl.revoke_role(role_id=role_id, user_id=user_id,
                                      tenant_id=project_id)

    def list_roles(self, user_id=None, project_id=None, domain_name=None):
        """List all roles."""
        if domain_name:
            raise NotImplementedError("Domain functionality not implemented "
                                      "in Keystone v2")
        if user_id:
            roles = self._impl.list_roles_for_user(user_id,
                                                   tenant_id=project_id)
        else:
            roles = self._impl.list_roles()
        return [self._unify_role(role) for role in roles]

    def create_ec2credentials(self, user_id, project_id):
        """Create ec2credentials.

        :param user_id: User ID for which to create credentials
        :param project_id: Project ID for which to create credentials

        :returns: Created ec2-credentials object
        """
        return self._impl.create_ec2credentials(user_id=user_id,
                                                tenant_id=project_id)
