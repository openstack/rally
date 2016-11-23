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

import collections

from rally.plugins.openstack import service


Project = collections.namedtuple("Project", ["id", "name", "domain_id"])
User = collections.namedtuple("User",
                              ["id", "name", "project_id", "domain_id"])
Service = collections.namedtuple("Service", ["id", "name"])
Role = collections.namedtuple("Role", ["id", "name"])


class Identity(service.UnifiedOpenStackService):
    @classmethod
    def is_applicable(cls, clients):
        cloud_version = clients.keystone().version.split(".")[0][1:]
        return cloud_version == cls._meta_get("impl")._meta_get("version")

    def create_project(self, project_name=None, domain_name="Default"):
        """Creates new project/tenant and return project object.

        :param project_name: Name of project to be created.
        :param domain_name: Name or id of domain where to create project, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        """
        return self._impl.create_project(project_name,
                                         domain_name=domain_name)

    def delete_project(self, project_id):
        """Deletes project."""
        return self._impl.delete_project(project_id)

    def list_projects(self):
        """List all projects."""
        return self._impl.list_projects()

    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param email: user's email
        :param project_id: user's default project
        :param domain_name: Name or id of domain where to create user, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        :param default_role: Name of role, for implementations that don't
                             support domains this argument must be None or
                             'member'.
        """
        return self._impl.create_user(username=username,
                                      password=password,
                                      email=email,
                                      project_id=project_id,
                                      domain_name=domain_name,
                                      default_role=default_role)

    def delete_user(self, user_id):
        """Deletes user by its id."""
        self._impl.delete_user(user_id)

    def list_users(self):
        """List all users."""
        return self._impl.list_users()

    def delete_service(self, service_id):
        """Deletes service."""
        self._impl.delete_service(service_id)

    def list_services(self):
        """List all services."""
        return self._impl.list_services()

    def create_role(self, name=None, domain_name="Default"):
        """Create role with specific name

        :param name: role name
        :param domain_name: Name or id of domain where to create role, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        """
        return self._impl.create_role(name=name, domain_name=domain_name)

    def add_role(self, role_id, user_id, project_id):
        """Add role to user."""
        return self._impl.add_role(role_id=role_id, user_id=user_id,
                                   project_id=project_id)

    def delete_role(self, role_id):
        """Deletes role."""
        self._impl.delete_role(role_id)

    def revoke_role(self, role_id, user_id, project_id):
        """Revokes a role from a user."""
        return self._impl.revoke_role(role_id=role_id, user_id=user_id,
                                      project_id=project_id)

    def list_roles(self, user_id=None, project_id=None, domain_name=None):
        """List all roles.

        :param user_id: filter in role grants for the specified user on a
            resource. Domain or project must be specified.
        :param project_id: filter in role grants on the specified project.
            user_id should be specified
        :param domain_name: filter in role grants on the specified domain.
            user_id should be specified
        """
        return self._impl.list_roles(user_id=user_id, project_id=project_id,
                                     domain_name=domain_name)

    def get_role(self, role_id):
        """Get role."""
        return self._impl.get_role(role_id)

    @staticmethod
    def _unify_service(service):
        return Service(id=service.id, name=service.name)

    @staticmethod
    def _unify_role(role):
        return Role(id=role.id, name=role.name)
