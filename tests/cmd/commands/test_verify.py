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

import mock
import uuid

from rally.cmd.commands import verify
from rally import consts
from tests import test


class VerifyCommandsTestCase(test.TestCase):
    def setUp(self):
        super(VerifyCommandsTestCase, self).setUp()
        self.verify = verify.VerifyCommands()
        self.endpoint = {'endpoints': [{'auth_url': 'fake_auth_url',
                                        'username': 'fake_username',
                                        'password': 'fake_password',
                                        'tenant_name': 'fake_tenant_name'}]}

        self.image1 = mock.Mock()
        self.image1.name = 'cirros-1'
        self.image1.id = 'fake_image_id_1'
        self.image2 = mock.Mock()
        self.image2.id = 'fake_image_id_2'
        self.image2.name = 'cirros-2'

        self.flavor1 = mock.Mock()
        self.flavor2 = mock.Mock()
        self.flavor1.id = 'fake_flavor_id_1'
        self.flavor2.id = 'fake_flavor_id_2'
        self.flavor1.ram = 128
        self.flavor2.ram = 64

    @mock.patch('rally.osclients.Clients')
    @mock.patch('rally.orchestrator.api.verify')
    def test_start(self, mock_verify, mock_clients):
        deploy_id = str(uuid.uuid4())
        mock_clients().glance().images.list.return_value = [
            self.image1, self.image2]
        mock_clients().nova().flavors.list.return_value = [
            self.flavor1, self.flavor2]

        self.verify.start(deploy_id)
        default_set_name = 'smoke'
        default_regex = None

        mock_verify.assert_called_once_with(deploy_id,
                                            default_set_name, default_regex)

    @mock.patch('rally.orchestrator.api.verify')
    def test_start_with_wrong_set_name(self, mock_verify):
        deploy_id = str(uuid.uuid4())

        wrong_set_name = 'unexpected_value'

        self.verify.start(deploy_id, wrong_set_name)

        self.assertNotIn(wrong_set_name, consts.TEMPEST_TEST_SETS)
        self.assertFalse(mock_verify.called)
