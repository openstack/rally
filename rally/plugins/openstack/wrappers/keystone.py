# Copyright 2014: Mirantis Inc.
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

import abc
import collections

from keystoneclient import exceptions
import six

from rally.common import logging


LOG = logging.getLogger(__name__)

Project = collections.namedtuple("Project", ["id", "name", "domain_id"])
User = collections.namedtuple("User",
                              ["id", "name", "project_id", "domain_id"])
Service = collections.namedtuple("Service", ["id", "name"])
Role = collections.namedtuple("Role", ["id", "name"])


@six.add_metaclass(abc.ABCMeta)
class KeystoneWrapper(object):
    def __init__(self, client):
        self.client = client

    def __getattr__(self, attr_name):
        return getattr(self.client, attr_name)

    @abc.abstractmethod
    def create_project(self, project_name, domain_name="Default"):
        """Creates new project/tenant and return project object.

        :param project_name: Name of project to be created.
        :param domain_name: Name or id of domain where to create project, for
                            implementations that don't support domains this
                            argument must be None or 'Default'.
        """

    @abc.abstractmethod
    def delete_project(self, project_id):
        """Deletes project."""

    @abc.abstractmethod
    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        """Create user.

        :param username: name of user
        :param password: user password
        :param project: user's default project
        :param domain_name: Name or id of domain where to create project, for
                            implementations that don't support domains this
                            argument must be None or 'Default'.
        :param default_role: user's default role
        """

    @abc.abstractmethod
    def delete_user(self, user_id):
        """Deletes user."""

    @abc.abstractmethod
    def list_users(self):
        """List all users."""

    @abc.abstractmethod
    def list_projects(self):
        """List all projects/tenants."""

    def delete_service(self, service_id):
        """Deletes service."""
        self.client.services.delete(service_id)

    def list_services(self):
        """List all services."""
        return map(KeystoneWrapper._wrap_service, self.client.services.list())

    def delete_role(self, role_id):
        """Deletes role."""
        self.client.roles.delete(role_id)

    def list_roles(self):
        """List all roles."""
        return map(KeystoneWrapper._wrap_role, self.client.roles.list())

    @abc.abstractmethod
    def add_role(self, role_id, user_id, project_id):
        """Assign role to user."""

    @abc.abstractmethod
    def remove_role(self, role_id, user_id, project_id):
        """Remove role from user."""

    @staticmethod
    def _wrap_service(service):
        return Service(id=service.id, name=service.name)

    @staticmethod
    def _wrap_role(role):
        return Role(id=role.id, name=role.name)


class KeystoneV2Wrapper(KeystoneWrapper):
    def _check_domain(self, domain_name):
        if domain_name.lower() != "default":
            raise NotImplementedError("Domain functionality not implemented "
                                      "in Keystone v2")

    @staticmethod
    def _wrap_v2_tenant(tenant):
        return Project(id=tenant.id, name=tenant.name, domain_id="default")

    @staticmethod
    def _wrap_v2_user(user):
        return User(id=user.id, name=user.name,
                    project_id=getattr(user, "tenantId", None),
                    domain_id="default")

    def create_project(self, project_name, domain_name="Default"):
        self._check_domain(domain_name)
        tenant = self.client.tenants.create(project_name)
        return KeystoneV2Wrapper._wrap_v2_tenant(tenant)

    def delete_project(self, project_id):
        self.client.tenants.delete(project_id)

    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        # NOTE(liuyulong): For v2 wrapper the `default_role` here is not used.
        self._check_domain(domain_name)
        user = self.client.users.create(username, password, email, project_id)
        return KeystoneV2Wrapper._wrap_v2_user(user)

    def delete_user(self, user_id):
        self.client.users.delete(user_id)

    def list_users(self):
        return map(KeystoneV2Wrapper._wrap_v2_user, self.client.users.list())

    def list_projects(self):
        return map(KeystoneV2Wrapper._wrap_v2_tenant,
                   self.client.tenants.list())

    def add_role(self, role_id, user_id, project_id):
        self.client.roles.add_user_role(user_id, role_id, tenant=project_id)

    def remove_role(self, role_id, user_id, project_id):
        self.client.roles.remove_user_role(user_id, role_id, tenant=project_id)


class KeystoneV3Wrapper(KeystoneWrapper):
    def _get_domain_id(self, domain_name_or_id):
        try:
            # First try to find domain by ID
            return self.client.domains.get(domain_name_or_id).id
        except exceptions.NotFound:
            # Domain not found by ID, try to find it by name
            domains = self.client.domains.list(name=domain_name_or_id)
            if domains:
                return domains[0].id
            # Domain not found by name, raise original NotFound exception
            raise

    @staticmethod
    def _wrap_v3_project(project):
        return Project(id=project.id, name=project.name,
                       domain_id=project.domain_id)

    @staticmethod
    def _wrap_v3_user(user):
        # When user has default_project_id that is None user.default_project_id
        # will raise AttributeError
        project_id = getattr(user, "default_project_id", None)
        return User(id=user.id, name=user.name, project_id=project_id,
                    domain_id=user.domain_id)

    def create_project(self, project_name, domain_name="Default"):
        domain_id = self._get_domain_id(domain_name)
        project = self.client.projects.create(
            name=project_name, domain=domain_id)
        return KeystoneV3Wrapper._wrap_v3_project(project)

    def delete_project(self, project_id):
        self.client.projects.delete(project_id)

    def create_user(self, username, password, email=None, project_id=None,
                    domain_name="Default", default_role="member"):
        domain_id = self._get_domain_id(domain_name)
        user = self.client.users.create(name=username, password=password,
                                        default_project=project_id,
                                        email=email, domain=domain_id)
        for role in self.client.roles.list():
            if default_role in role.name.lower():
                self.client.roles.grant(role.id, user=user.id,
                                        project=project_id)
                break
        else:
            LOG.warning(
                "Unable to set %s role to created user." % default_role)
        return KeystoneV3Wrapper._wrap_v3_user(user)

    def delete_user(self, user_id):
        self.client.users.delete(user_id)

    def list_users(self):
        return map(KeystoneV3Wrapper._wrap_v3_user, self.client.users.list())

    def list_projects(self):
        return map(KeystoneV3Wrapper._wrap_v3_project,
                   self.client.projects.list())

    def add_role(self, role_id, user_id, project_id):
        self.client.roles.grant(role_id, user=user_id, project=project_id)

    def remove_role(self, role_id, user_id, project_id):
        self.client.roles.revoke(role_id, user=user_id, project=project_id)


def wrap(client):
    """Returns keystone wrapper based on keystone client version."""

    if client.version == "v2.0":
        return KeystoneV2Wrapper(client)
    elif client.version == "v3":
        return KeystoneV3Wrapper(client)
    else:
        raise NotImplementedError(
            "Wrapper for version %s is not implemented." % client.version)
