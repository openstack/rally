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

import uuid

import mock
import six

from rally.cmd.commands import verify
from rally import consts
from rally import objects
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

    @mock.patch('rally.openstack.common.cliutils.print_list')
    @mock.patch('rally.db.verification_list')
    def test_list(self, mock_db_verification_list, mock_print_list):
        fields = ['UUID', 'Deployment UUID', 'Set name', 'Tests', 'Failures',
                  'Created at', 'Status']
        verifications = {'dummy': []}
        mock_db_verification_list.return_value = verifications
        self.verify.list()
        mock_db_verification_list.assert_called_once()
        mock_print_list.assert_called_once_with(verifications, fields,
                                                sortby_index=fields.index(
                                                    'Created at'))

    @mock.patch('rally.openstack.common.cliutils.print_list')
    @mock.patch('rally.db.verification_get')
    @mock.patch('rally.db.verification_result_get')
    @mock.patch('rally.objects.Verification')
    def test_show(self, mock_obj_verification,
                  mock_verification_result_get, mock_verification_get,
                  mock_print_list):

        class Test_dummy():
            data = {'test_cases': {'test_a': {'name': 'test_a', 'time': 20,
                                              'status': 'PASS'},
                                   'test_b': {'name': 'test_b', 'time': 20,
                                              'status': 'SKIP'},
                                   'test_c': {'name': 'test_c', 'time': 20,
                                              'status': 'FAIL'}}}

        verification_id = '39121186-b9a4-421d-b094-6c6b270cf9e9'
        total_fields = ['UUID', 'Deployment UUID', 'Set name', 'Tests',
                        'Failures', 'Created at', 'Status']
        fields = ['name', 'time', 'status']
        verification = mock.MagicMock()
        tests = Test_dummy()
        mock_verification_result_get.return_value = tests
        mock_verification_get.return_value = verification
        mock_obj_verification.return_value = 1
        values = map(objects.Verification,
                     six.itervalues(tests.data['test_cases']))
        self.verify.show(verification_id)
        mock_print_list.assert_any_call(
                [verification], fields=total_fields,
                sortby_index=total_fields.index('Created at'))
        mock_verification_get.assert_called_once_with(verification_id)
        mock_verification_result_get.assert_called_once_with(verification_id)
        mock_print_list.assert_any_call(values, fields, sortby_index=0)
