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

    @service.should_be_overridden
    def create_project(self, project_name=None, domain_name="Default"):
        """Creates new project/tenant and return project object.

        :param project_name: Name of project to be created.
        :param domain_name: Name or id of domain where to create project, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        """
        return self._impl.create_project(project_name,
                                         domain_name=domain_name)

    @service.should_be_overridden
    def update_project(self, project_id, name=None, enabled=None,
                       description=None):
        """Update project name, enabled and description

        :param project_id: Id of project to update
        :param name: project name to be set
        :param enabled: enabled status of project
        :param description: project description to be set
        """
        self._impl.update_project(project_id, name=name, enabled=enabled,
                                  description=description)

    @service.should_be_overridden
    def delete_project(self, project_id):
        """Deletes project."""
        return self._impl.delete_project(project_id)

    @service.should_be_overridden
    def list_projects(self):
        """List all projects."""
        return self._impl.list_projects()

    @service.should_be_overridden
    def get_project(self, project_id):
        """Get project."""
        return self._impl.get_project(project_id)

    @service.should_be_overridden
    def create_user(self, username=None, password=None, project_id=None,
                    domain_name="Default", enabled=True,
                    default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param project_id: user's default project
        :param domain_name: Name or id of domain where to create user, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        :param enabled: whether the user is enabled.
        :param default_role: Name of role, for implementations that don't
                             support domains this argument must be None or
                             'member'.
        """
        return self._impl.create_user(username=username,
                                      password=password,
                                      project_id=project_id,
                                      domain_name=domain_name,
                                      default_role=default_role)

    @service.should_be_overridden
    def create_users(self, owner_id, number_of_users, user_create_args=None):
        """Create specified amount of users.

        :param owner_id: Id of tenant/project
        :param number_of_users: number of users to create
        :param user_create_args: additional user creation arguments
        """
        return self._impl.create_users(owner_id,
                                       number_of_users=number_of_users,
                                       user_create_args=user_create_args)

    @service.should_be_overridden
    def delete_user(self, user_id):
        """Deletes user by its id."""
        self._impl.delete_user(user_id)

    @service.should_be_overridden
    def list_users(self):
        """List all users."""
        return self._impl.list_users()

    @service.should_be_overridden
    def update_user(self, user_id, enabled=None, name=None, email=None,
                    password=None):
        return self._impl.update_user(user_id, enabled=enabled, name=name,
                                      email=email, password=password)

    @service.should_be_overridden
    def get_user(self, user_id):
        """Get user."""
        return self._impl.get_user(user_id)

    @service.should_be_overridden
    def create_service(self, name=None, service_type=None, description=None):
        """Creates keystone service with random name.

        :param name: name of service to create
        :param service_type: type of the service
        :param description: description of the service
        """
        return self._impl.create_service(name=name, service_type=service_type,
                                         description=description)

    @service.should_be_overridden
    def delete_service(self, service_id):
        """Deletes service."""
        self._impl.delete_service(service_id)

    @service.should_be_overridden
    def list_services(self):
        """List all services."""
        return self._impl.list_services()

    @service.should_be_overridden
    def get_service(self, service_id):
        """Get service."""
        return self._impl.get_service(service_id)

    @service.should_be_overridden
    def create_role(self, name=None, domain_name="Default"):
        """Create role with specific name

        :param name: role name
        :param domain_name: Name or id of domain where to create role, for
                            those service implementations that don't support
                            domains you should use None or 'Default' value.
        """
        return self._impl.create_role(name=name, domain_name=domain_name)

    @service.should_be_overridden
    def add_role(self, role_id, user_id, project_id):
        """Add role to user."""
        return self._impl.add_role(role_id=role_id, user_id=user_id,
                                   project_id=project_id)

    @service.should_be_overridden
    def delete_role(self, role_id):
        """Deletes role."""
        self._impl.delete_role(role_id)

    @service.should_be_overridden
    def revoke_role(self, role_id, user_id, project_id):
        """Revokes a role from a user."""
        return self._impl.revoke_role(role_id=role_id, user_id=user_id,
                                      project_id=project_id)

    @service.should_be_overridden
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

    @service.should_be_overridden
    def get_role(self, role_id):
        """Get role."""
        return self._impl.get_role(role_id)

    @service.should_be_overridden
    def get_service_by_name(self, name):
        """List all services to find proper one."""
        return self._impl.get_service_by_name(name)

    @service.should_be_overridden
    def create_ec2credentials(self, user_id, project_id):
        """Create ec2credentials.

        :param user_id: User ID for which to create credentials
        :param project_id: Project ID for which to create credentials

        :returns: Created ec2-credentials object
        """
        return self._impl.create_ec2credentials(user_id=user_id,
                                                project_id=project_id)

    @service.should_be_overridden
    def list_ec2credentials(self, user_id):
        """List of access/secret pairs for a user_id.

        :param user_id: List all ec2-credentials for User ID

        :returns: Return ec2-credentials list
        """
        return self._impl.list_ec2credentials(user_id)

    @service.should_be_overridden
    def delete_ec2credential(self, user_id, access):
        """Delete ec2credential.

        :param user_id: User ID for which to delete credential
        :param access: access key for ec2credential to delete
        """
        return self._impl.delete_ec2credential(user_id=user_id, access=access)

    @service.should_be_overridden
    def fetch_token(self):
        """Authenticate user token."""
        return self._impl.fetch_token()

    @service.should_be_overridden
    def validate_token(self, token):
        """Validate user token.

        :param token: Auth token to validate
        """
        return self._impl.validate_token(token)
