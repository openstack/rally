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

from rally.plugins.openstack import service
from rally.plugins.openstack.services.identity import identity
from rally.task import atomic


@service.service("keystone", service_type="identity", version="2")
class KeystoneV2Service(service.Service):

    @atomic.action_timer("keystone_v2.create_tenant")
    def create_tenant(self, tenant_name=None):
        tenant_name = tenant_name or self.generate_random_name()
        return self._clients.keystone("2").tenants.create(tenant_name)

    @atomic.action_timer("keystone_v2.delete_tenant")
    def delete_tenant(self, tenant_id):
        return self._clients.keystone("2").tenants.delete(tenant_id)

    @atomic.action_timer("keystone_v2.list_tenants")
    def list_tenants(self):
        return self._clients.keystone("2").tenants.list()

    @atomic.action_timer("keystone_v2.create_user")
    def create_user(self, username, password, email=None, tenant_id=None):
        return self._clients.keystone("2").users.create(name=username,
                                                        password=password,
                                                        email=email,
                                                        tenant_id=tenant_id)

    @atomic.action_timer("keystone_v2.list_users")
    def list_users(self):
        return self._clients.keystone("2").users.list()

    @atomic.action_timer("keystone_v2.delete_user")
    def delete_user(self, user_id):
        """Deletes user by its id."""
        self._clients.keystone("2").users.delete(user_id)

    @atomic.action_timer("keystone_v2.delete_service")
    def delete_service(self, service_id):
        """Deletes service."""
        self._clients.keystone("2").services.delete(service_id)

    @atomic.action_timer("keystone.list_services")
    def list_services(self):
        """List all services."""
        return self._clients.keystone("2").services.list()

    @atomic.action_timer("keystone_v2.create_role")
    def create_role(self, name=None):
        name = name or self.generate_random_name()
        return self._clients.keystone("2").roles.create(name)

    @atomic.action_timer("keystone_v2.add_role")
    def add_role(self, role_id, user_id, tenant_id):
        return self._clients.keystone("2").roles.add_user_role(
            user=user_id, role=role_id, tenant=tenant_id)

    @atomic.action_timer("keystone.delete_role")
    def delete_role(self, role_id):
        """Deletes role."""
        self._clients.keystone("2").roles.delete(role_id)

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

    @atomic.action_timer("keystone_v2.get_role")
    def get_role(self, role_id):
        """Get role."""
        return self._clients.keystone("2").roles.get(role_id)


@service.compat_layer(KeystoneV2Service)
class UnifiedKeystoneV2Service(identity.Identity):
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

    def delete_project(self, project_id):
        """Deletes project."""
        return self._impl.delete_tenant(project_id)

    def list_projects(self):
        """List all projects."""
        return [self._unify_tenant(t) for t in self._impl.list_tenants()]

    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param email: user's email
        :param project_id: user's default project
        :param domain_name: Restricted for Keystone V2. Should not be set or
            "Default" is expected.
        :param default_role: Restricted for Keystone V2. Should not be set or
            "member" is expected.
        """
        self._check_domain(domain_name)
        user = self._impl.create_user(username=username,
                                      password=password,
                                      email=email,
                                      tenant_id=project_id)
        return self._unify_user(user)

    def delete_user(self, user_id):
        """Deletes user by its id."""
        return self._impl.delete_user(user_id)

    def list_users(self):
        """List all users."""
        return [self._unify_user(u) for u in self._impl.list_users()]

    def delete_service(self, service_id):
        """Deletes service."""
        return self._impl.delete_service(service_id)

    def list_services(self):
        """List all services."""
        return [self._unify_service(s) for s in self._impl.list_services()]

    def create_role(self, name=None, domain_name="Default"):
        """Add role to user."""
        self._check_domain(domain_name)
        return self._unify_role(self._impl.create_role(name))

    def add_role(self, role_id, user_id, project_id):
        """Add role to user."""
        return self._unify_role(self._impl.add_role(
            role_id=role_id, user_id=user_id, tenant_id=project_id))

    def delete_role(self, role_id):
        """Deletes role."""
        return self._impl.delete_role(role_id)

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

    def get_role(self, role_id):
        """Get role."""
        return self._unify_role(self._impl.get_role(role_id))
