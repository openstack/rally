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
from rally import exceptions
from rally.plugins.openstack import service
from rally.plugins.openstack.services.identity import identity
from rally.task import atomic


LOG = logging.getLogger(__name__)


@service.service("keystone", service_type="identity", version="3")
class KeystoneV3Service(service.Service):

    def _get_domain_id(self, domain_name_or_id):
        from keystoneclient import exceptions as kc_exceptions

        try:
            # First try to find domain by ID
            return self._clients.keystone("3").domains.get(
                domain_name_or_id).id
        except kc_exceptions.NotFound:
            # Domain not found by ID, try to find it by name
            domains = self._clients.keystone("3").domains.list(
                name=domain_name_or_id)
            if domains:
                return domains[0].id
            # Domain not found by name
            raise exceptions.GetResourceNotFound(
                resource="KeystoneDomain(%s)" % domain_name_or_id)

    @atomic.action_timer("keystone_v3.create_project")
    def create_project(self, project_name=None, domain_name="Default"):
        project_name = project_name or self.generate_random_name()
        domain_id = self._get_domain_id(domain_name)
        return self._clients.keystone("3").projects.create(name=project_name,
                                                           domain=domain_id)

    @atomic.action_timer("keystone_v3.delete_project")
    def delete_project(self, project_id):
        self._clients.keystone("3").projects.delete(project_id)

    @atomic.action_timer("keystone_v3.list_projects")
    def list_projects(self):
        return self._clients.keystone("3").projects.list()

    @atomic.action_timer("keystone_v3.create_user")
    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        """Create user.


        :param username: name of user
        :param password: user password
        :param email: user'ss email
        :param project_id: user's default project
        :param domain_name: Name or id of domain where to create project.
        :param default_role: user's default role
        """
        domain_id = self._get_domain_id(domain_name)
        user = self._clients.keystone("3").users.create(
            name=username, password=password, default_project=project_id,
            email=email, domain=domain_id)
        for role in self.list_roles():
            if default_role in role.name.lower():
                self.add_role(role_id=role.id,
                              user_id=user.id,
                              project_id=project_id)
                break
        else:
            LOG.warning("Unable to set %s role to created user." %
                        default_role)
        return user

    @atomic.action_timer("keystone_v3.list_users")
    def list_users(self):
        return self._clients.keystone("3").users.list()

    @atomic.action_timer("keystone_v3.delete_user")
    def delete_user(self, user_id):
        """Deletes user by its id."""
        self._clients.keystone("3").users.delete(user_id)

    @atomic.action_timer("keystone_v3.delete_service")
    def delete_service(self, service_id):
        """Deletes service."""
        self._clients.keystone("3").services.delete(service_id)

    @atomic.action_timer("keystone_v3.list_services")
    def list_services(self):
        """List all services."""
        return self._clients.keystone("3").services.list()

    @atomic.action_timer("keystone_v3.create_role")
    def create_role(self, name=None, domain_name="Default"):
        domain_id = self._get_domain_id(domain_name)
        name = name or self.generate_random_name()
        return self._clients.keystone("3").roles.create(name, domain=domain_id)

    @atomic.action_timer("keystone_v3.add_role")
    def add_role(self, role_id, user_id, project_id):
        return self._clients.keystone("3").roles.grant(role=role_id,
                                                       user=user_id,
                                                       project=project_id)

    @atomic.action_timer("keystone_v3.delete_role")
    def delete_role(self, role_id):
        """Deletes role."""
        self._clients.keystone("3").roles.delete(role_id)

    @atomic.action_timer("keystone_v3.list_roles")
    def list_roles(self, user_id=None, project_id=None, domain_name=None):
        """List all roles."""
        domain_id = None
        if domain_name:
            domain_id = self._get_domain_id(domain_name)
        return self._clients.keystone("3").roles.list(user=user_id,
                                                      project=project_id,
                                                      domain=domain_id)

    @atomic.action_timer("keystone_v3.revoke_role")
    def revoke_role(self, role_id, user_id, project_id):
        self._clients.keystone("3").roles.revoke(role=role_id,
                                                 user=user_id,
                                                 project=project_id)

    @atomic.action_timer("keystone_v3.get_role")
    def get_role(self, role_id):
        """Get role."""
        return self._clients.keystone("3").roles.get(role_id)

    @atomic.action_timer("keystone_v3.create_domain")
    def create_domain(self, name, description=None, enabled=True):
        return self._clients.keystone("3").domains.create(
            name, description=description, enabled=enabled)


@service.compat_layer(KeystoneV3Service)
class UnifiedKeystoneV3Service(identity.Identity):

    @staticmethod
    def _unify_project(project):
        return identity.Project(id=project.id, name=project.name,
                                domain_id=project.domain_id)

    @staticmethod
    def _unify_user(user):
        # When user has default_project_id that is None user.default_project_id
        # will raise AttributeError
        project_id = getattr(user, "default_project_id", None)
        return identity.User(id=user.id, name=user.name, project_id=project_id,
                             domain_id=user.domain_id)

    def create_project(self, project_name=None, domain_name="Default"):
        """Creates new project/tenant and return project object.

        :param project_name: Name of project to be created.
        :param domain_name: Name or id of domain where to create project,
        """
        project = self._impl.create_project(project_name)
        return self._unify_project(project)

    def delete_project(self, project_id):
        """Deletes project."""
        return self._impl.delete_project(project_id)

    def list_projects(self):
        """List all projects."""
        return [self._unify_project(p) for p in self._impl.list_projects()]

    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param email: user's email
        :param project_id: user's default project
        :param domain_name: Name or id of domain where to create project,
        :param default_role: Name of default user's role
        """
        return self._unify_user(self._impl.create_user(
            username=username, password=password, email=email,
            project_id=project_id, domain_name=domain_name,
            default_role=default_role))

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
        return self._unify_role(self._impl.create_role(
            name, domain_name=domain_name))

    def add_role(self, role_id, user_id, project_id):
        """Add role to user."""
        return self._unify_role(self._impl.add_role(
            role_id=role_id, user_id=user_id, project_id=project_id))

    def delete_role(self, role_id):
        """Deletes role."""
        return self._impl.delete_role(role_id)

    def revoke_role(self, role_id, user_id, project_id):
        """Revokes a role from a user."""
        return self._impl.revoke_role(role_id=role_id, user_id=user_id,
                                      project_id=project_id)

    def list_roles(self, user_id=None, project_id=None, domain_name=None):
        """List all roles."""
        return [self._unify_role(role) for role in self._impl.list_roles(
            user_id=user_id, project_id=project_id, domain_name=domain_name)]

    def get_role(self, role_id):
        """Get role."""
        return self._unify_role(self._impl.get_role(role_id))
