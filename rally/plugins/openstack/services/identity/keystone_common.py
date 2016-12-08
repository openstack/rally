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

from rally import osclients
from rally.plugins.openstack.services.identity import identity
from rally.task import atomic


class UnifiedKeystoneMixin(object):
    @staticmethod
    def _unify_service(service):
        return identity.Service(id=service.id, name=service.name)

    @staticmethod
    def _unify_role(role):
        return identity.Role(id=role.id, name=role.name)

    def delete_user(self, user_id):
        """Deletes user by its id."""
        return self._impl.delete_user(user_id)

    def get_user(self, user_id):
        """Get user."""
        return self._unify_user(self._impl.get_user(user_id))

    def create_service(self, name=None, service_type=None, description=None):
        """Creates keystone service."""

        return self._unify_service(self._impl.create_service(
            name=name, service_type=service_type, description=description))

    def delete_service(self, service_id):
        """Deletes service."""
        return self._impl.delete_service(service_id)

    def get_service(self, service_id):
        """Get service."""
        return self._unify_service(self._impl.get_service(service_id))

    def get_service_by_name(self, name):
        """List all services to find proper one."""
        return self._unify_service(self._impl.get_service_by_name(name))

    def get_role(self, role_id):
        """Get role."""
        return self._unify_role(self._impl.get_role(role_id))

    def delete_role(self, role_id):
        """Deletes role."""
        return self._impl.delete_role(role_id)

    def list_ec2credentials(self, user_id):
        """List of access/secret pairs for a user_id.

        :param user_id: List all ec2-credentials for User ID

        :returns: Return ec2-credentials list
        """
        return self._impl.list_ec2credentials(user_id)

    def delete_ec2credential(self, user_id, access):
        """Delete ec2credential.

        :param user_id: User ID for which to delete credential
        :param access: access key for ec2credential to delete
        """
        return self._impl.delete_ec2credential(user_id=user_id, access=access)

    def fetch_token(self):
        """Authenticate user token."""
        return self._impl.fetch_token()

    def validate_token(self, token):
        """Validate user token.

        :param token: Auth token to validate
        """
        return self._impl.validate_token(token)


class KeystoneMixin(object):

    def list_users(self):
        aname = "keystone_v%s.list_users" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).users.list()

    def delete_user(self, user_id):
        """Deletes user by its id."""
        aname = "keystone_v%s.delete_user" % self.version
        with atomic.ActionTimer(self, aname):
            self._clients.keystone(self.version).users.delete(user_id)

    def get_user(self, user_id):
        """Get user by its id."""
        aname = "keystone_v%s.get_user" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).users.get(user_id)

    def delete_service(self, service_id):
        """Deletes service."""
        aname = "keystone_v%s.delete_service" % self.version
        with atomic.ActionTimer(self, aname):
            self._clients.keystone(self.version).services.delete(service_id)

    def list_services(self):
        """List all services."""
        aname = "keystone_v%s.list_services" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).services.list()

    def get_service(self, service_id):
        """Get service."""
        aname = "keystone_v%s.get_services" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).services.get(
                service_id)

    def get_service_by_name(self, name):
        """List all services to find proper one."""
        for s in self.list_services():
            if s.name == name:
                return s

    def delete_role(self, role_id):
        """Deletes role."""
        aname = "keystone_v%s.delete_role" % self.version
        with atomic.ActionTimer(self, aname):
            self._clients.keystone(self.version).roles.delete(role_id)

    def list_roles(self):
        """List all roles."""
        aname = "keystone_v%s.list_roles" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).roles.list()

    def get_role(self, role_id):
        """Get role."""
        aname = "keystone_v%s.get_role" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).roles.get(role_id)

    def list_ec2credentials(self, user_id):
        """List of access/secret pairs for a user_id.

        :param user_id: List all ec2-credentials for User ID

        :returns: Return ec2-credentials list
        """
        aname = "keystone_v%s.list_ec2creds" % self.version
        with atomic.ActionTimer(self, aname):
            return self._clients.keystone(self.version).ec2.list(user_id)

    def delete_ec2credential(self, user_id, access):
        """Delete ec2credential.

        :param user_id: User ID for which to delete credential
        :param access: access key for ec2credential to delete
        """
        aname = "keystone_v%s.delete_ec2creds" % self.version
        with atomic.ActionTimer(self, aname):
            self._clients.keystone(self.version).ec2.delete(user_id=user_id,
                                                            access=access)

    def fetch_token(self):
        """Authenticate user token."""
        cred = self._clients.credential
        aname = "keystone_v%s.fetch_token" % self.version
        with atomic.ActionTimer(self, aname):
            clients = osclients.Clients(credential=cred,
                                        api_info=self._clients.api_info)
            return clients.keystone.auth_ref.auth_token

    def validate_token(self, token):
        """Validate user token.

        :param token: Auth token to validate
        """
        aname = "keystone_v%s.validate_token" % self.version
        with atomic.ActionTimer(self, aname):
            self._clients.keystone(self.version).tokens.validate(token)
