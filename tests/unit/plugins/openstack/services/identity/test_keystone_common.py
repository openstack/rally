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

import mock

from rally.plugins.openstack import service
from rally.plugins.openstack.services.identity import identity
from rally.plugins.openstack.services.identity import keystone_common
from tests.unit import test


class FullUnifiedKeystone(keystone_common.UnifiedKeystoneMixin,
                          service.Service):
    """Implementation of UnifiedKeystoneMixin with Service base class."""
    pass


class UnifiedKeystoneMixinTestCase(test.TestCase):
    def setUp(self):
        super(UnifiedKeystoneMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.name_generator = mock.MagicMock()
        self.impl = mock.MagicMock()
        self.version = "some"
        self.service = FullUnifiedKeystone(
            clients=self.clients, name_generator=self.name_generator)
        self.service._impl = self.impl
        self.service.version = self.version

    def test__unify_service(self):
        class SomeFakeService(object):
            id = 123123123123123
            name = "asdfasdfasdfasdfadf"
            other_var = "asdfasdfasdfasdfasdfasdfasdf"

        service = self.service._unify_service(SomeFakeService())
        self.assertIsInstance(service, identity.Service)
        self.assertEqual(SomeFakeService.id, service.id)
        self.assertEqual(SomeFakeService.name, service.name)

    def test__unify_role(self):
        class SomeFakeRole(object):
            id = 123123123123123
            name = "asdfasdfasdfasdfadf"
            other_var = "asdfasdfasdfasdfasdfasdfasdf"

        role = self.service._unify_role(SomeFakeRole())
        self.assertIsInstance(role, identity.Role)
        self.assertEqual(SomeFakeRole.id, role.id)
        self.assertEqual(SomeFakeRole.name, role.name)

    def test_delete_user(self):
        user_id = "id"

        self.service.delete_user(user_id)
        self.impl.delete_user.assert_called_once_with(user_id)

    def test_get_user(self):
        user_id = "id"

        self.service._unify_user = mock.MagicMock()

        self.assertEqual(self.service._unify_user.return_value,
                         self.service.get_user(user_id))

        self.impl.get_user.assert_called_once_with(user_id)
        self.service._unify_user.assert_called_once_with(
            self.impl.get_user.return_value)

    def test_create_service(self):
        self.service._unify_service = mock.MagicMock()

        name = "some_Service"
        service_type = "computeNextGen"
        description = "we will Rock you!"

        self.assertEqual(self.service._unify_service.return_value,
                         self.service.create_service(
                             name=name, service_type=service_type,
                             description=description))

        self.service._unify_service.assert_called_once_with(
            self.service._impl.create_service.return_value)
        self.service._impl.create_service.assert_called_once_with(
            name=name, service_type=service_type, description=description)

    def test_delete_service(self):
        service_id = "id"

        self.service.delete_service(service_id)
        self.impl.delete_service.assert_called_once_with(service_id)

    def test_get_service(self):
        service_id = "id"

        self.service._unify_service = mock.MagicMock()

        self.assertEqual(self.service._unify_service.return_value,
                         self.service.get_service(service_id))

        self.impl.get_service.assert_called_once_with(service_id)
        self.service._unify_service.assert_called_once_with(
            self.impl.get_service.return_value)

    def test_get_service_by_name(self):
        service_id = "id"

        self.service._unify_service = mock.MagicMock()

        self.assertEqual(self.service._unify_service.return_value,
                         self.service.get_service_by_name(service_id))

        self.impl.get_service_by_name.assert_called_once_with(service_id)
        self.service._unify_service.assert_called_once_with(
            self.impl.get_service_by_name.return_value)

    def test_delete_role(self):
        role_id = "id"

        self.service.delete_role(role_id)
        self.impl.delete_role.assert_called_once_with(role_id)

    def test_get_role(self):
        role_id = "id"

        self.service._unify_role = mock.MagicMock()

        self.assertEqual(self.service._unify_role.return_value,
                         self.service.get_role(role_id))

        self.impl.get_role.assert_called_once_with(role_id)
        self.service._unify_role.assert_called_once_with(
            self.impl.get_role.return_value)

    def test_list_ec2credentials(self):
        user_id = "id"
        self.assertEqual(self.impl.list_ec2credentials.return_value,
                         self.service.list_ec2credentials(user_id))

        self.impl.list_ec2credentials.assert_called_once_with(user_id)

    def test_delete_ec2credential(self):
        user_id = "id"
        access = mock.MagicMock()

        self.assertEqual(self.impl.delete_ec2credential.return_value,
                         self.service.delete_ec2credential(user_id,
                                                           access=access))

        self.impl.delete_ec2credential.assert_called_once_with(user_id=user_id,
                                                               access=access)

    def test_fetch_token(self):

        self.assertEqual(self.impl.fetch_token.return_value,
                         self.service.fetch_token())

        self.impl.fetch_token.assert_called_once_with()

    def test_validate_token(self):
        token = "id"

        self.assertEqual(self.impl.validate_token.return_value,
                         self.service.validate_token(token))

        self.impl.validate_token.assert_called_once_with(token)


class FullKeystone(service.Service, keystone_common.KeystoneMixin):
    """Implementation of KeystoneMixin with Service base class."""
    pass


class KeystoneMixinTestCase(test.TestCase):
    def setUp(self):
        super(KeystoneMixinTestCase, self).setUp()
        self.clients = mock.MagicMock()
        self.kc = self.clients.keystone.return_value
        self.name_generator = mock.MagicMock()
        self.version = "some"
        self.service = FullKeystone(
            clients=self.clients, name_generator=self.name_generator)
        self.service.version = self.version

    def test_list_users(self):
        self.assertEqual(self.kc.users.list.return_value,
                         self.service.list_users())
        self.kc.users.list.assert_called_once_with()

    def test_delete_user(self):
        user_id = "fake_id"
        self.service.delete_user(user_id)
        self.kc.users.delete.assert_called_once_with(user_id)

    def test_get_user(self):
        user_id = "fake_id"
        self.service.get_user(user_id)
        self.kc.users.get.assert_called_once_with(user_id)

    def test_delete_service(self):
        service_id = "fake_id"
        self.service.delete_service(service_id)
        self.kc.services.delete.assert_called_once_with(service_id)

    def test_list_services(self):
        self.assertEqual(self.kc.services.list.return_value,
                         self.service.list_services())
        self.kc.services.list.assert_called_once_with()

    def test_get_service(self):
        service_id = "fake_id"
        self.service.get_service(service_id)
        self.kc.services.get.assert_called_once_with(service_id)

    def test_get_service_by_name(self):
        class FakeService(object):
            def __init__(self, name):
                self.name = name
        service_name = "fake_name"
        services = [FakeService(name="foo"), FakeService(name=service_name),
                    FakeService(name="bar")]
        self.service.list_services = mock.MagicMock(return_value=services)

        self.assertEqual(services[1],
                         self.service.get_service_by_name(service_name))

    def test_delete_role(self):
        role_id = "fake_id"
        self.service.delete_role(role_id)
        self.kc.roles.delete.assert_called_once_with(role_id)

    def test_list_roles(self):
        self.assertEqual(self.kc.roles.list.return_value,
                         self.service.list_roles())
        self.kc.roles.list.assert_called_once_with()

    def test_get_role(self):
        role_id = "fake_id"
        self.service.get_role(role_id)
        self.kc.roles.get.assert_called_once_with(role_id)

    def test_list_ec2credentials(self):
        user_id = "fake_id"

        self.assertEqual(self.kc.ec2.list.return_value,
                         self.service.list_ec2credentials(user_id))
        self.kc.ec2.list.assert_called_once_with(user_id)

    def test_delete_ec2credentials(self):
        user_id = "fake_id"
        access = mock.MagicMock()

        self.service.delete_ec2credential(user_id, access=access)
        self.kc.ec2.delete.assert_called_once_with(user_id=user_id,
                                                   access=access)

    @mock.patch("rally.osclients.Clients")
    def test_fetch_token(self, mock_clients):
        expected_token = mock_clients.return_value.keystone.auth_ref.auth_token
        self.assertEqual(expected_token, self.service.fetch_token())
        mock_clients.assert_called_once_with(
            credential=self.clients.credential,
            api_info=self.clients.api_info)

    def test_validate_token(self):
        token = "some_token"

        self.service.validate_token(token)
        self.kc.tokens.validate.assert_called_once_with(token)
