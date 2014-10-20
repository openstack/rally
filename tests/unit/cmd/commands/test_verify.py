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

import tempfile

import mock
import six

from rally.cmd.commands import verify
from rally import consts
from rally import exceptions
from rally import objects
from tests.unit import test


class VerifyCommandsTestCase(test.TestCase):
    def setUp(self):
        super(VerifyCommandsTestCase, self).setUp()
        self.verify = verify.VerifyCommands()

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
        deploy_id = '0fba91c6-82d5-4ce1-bd00-5d7c989552d9'
        mock_clients().glance().images.list.return_value = [
            self.image1, self.image2]
        mock_clients().nova().flavors.list.return_value = [
            self.flavor1, self.flavor2]

        self.verify.start(deploy_id=deploy_id)
        default_set_name = 'smoke'
        default_regex = None

        mock_verify.assert_called_once_with(deploy_id,
                                            default_set_name, default_regex,
                                            None)

    @mock.patch('rally.osclients.Clients')
    @mock.patch('rally.orchestrator.api.verify')
    def test_start_with_user_specified_tempest_config(self, mock_verify,
                                                      mock_clients):
        deploy_id = '0fba91c6-82d5-4ce1-bd00-5d7c989552d9'
        mock_clients().glance().images.list.return_value = [
            self.image1, self.image2]
        mock_clients().nova().flavors.list.return_value = [
            self.flavor1, self.flavor2]
        tempest_config = tempfile.NamedTemporaryFile()
        self.verify.start(deploy_id=deploy_id,
                          tempest_config=tempest_config.name)
        default_set_name = 'smoke'
        default_regex = None

        mock_verify.assert_called_once_with(deploy_id,
                                            default_set_name, default_regex,
                                            tempest_config.name)
        tempest_config.close()

    @mock.patch('rally.orchestrator.api.verify')
    def test_start_with_wrong_set_name(self, mock_verify):
        deploy_id = 'f2009aae-6ef3-468e-96b2-3c987d584010'

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
        mock_db_verification_list.assert_called_once_with()
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
                [verification], fields=total_fields)
        mock_verification_get.assert_called_once_with(verification_id)
        mock_verification_result_get.assert_called_once_with(verification_id)
        mock_print_list.assert_any_call(values, fields, sortby_index=0)

    @mock.patch('rally.db.verification_result_get', return_value={'data': {}})
    @mock.patch('json.dumps')
    def test_results(self, mock_json_dumps, mock_db_result_get):
        verification_uuid = 'a0231bdf-6a4e-4daf-8ab1-ae076f75f070'
        self.verify.results(verification_uuid, output_json=True)

        mock_db_result_get.assert_called_once_with(verification_uuid)
        mock_json_dumps.assert_called_once_with({})

    @mock.patch('rally.db.verification_result_get')
    def test_results_verification_not_found(self, mock_db_result_get):
        verification_uuid = '9044ced5-9c84-4666-8a8f-4b73a2b62acb'
        mock_db_result_get.side_effect = exceptions.NotFoundException()
        self.assertEqual(self.verify.results(verification_uuid), 1)

        mock_db_result_get.assert_called_once_with(verification_uuid)

    @mock.patch('rally.cmd.commands.verify.open', create=True)
    @mock.patch('rally.db.verification_result_get', return_value={'data': {}})
    def test_results_with_output_json_and_output_file(self,
                                                      mock_db_result_get,
                                                      mock_open):
        mock_open.return_value = mock.MagicMock()
        verification_uuid = '94615cd4-ff45-4123-86bd-4b0741541d09'
        self.verify.results(verification_uuid, output_file='results',
                            output_json=True)

        mock_db_result_get.assert_called_once_with(verification_uuid)
        mock_open.assert_called_once_with('results', 'wb')
        fake_file = mock_open.return_value.__enter__.return_value
        fake_file.write.assert_called_once_with('{}')

    @mock.patch('rally.cmd.commands.verify.open', create=True)
    @mock.patch('rally.db.verification_result_get', return_value={'data': {}})
    def test_results_with_output_pprint_and_output_file(self,
                                                        mock_db_result_get,
                                                        mock_open):
        mock_open.return_value = mock.MagicMock()
        verification_uuid = 'fa882ccc-153e-4a6e-9001-91fecda6a75c'
        self.verify.results(verification_uuid, output_pprint=True,
                            output_file='results')

        mock_db_result_get.assert_called_once_with(verification_uuid)
        mock_open.assert_called_once_with('results', 'wb')
        fake_file = mock_open.return_value.__enter__.return_value
        fake_file.write.assert_called_once_with('{}')

    @mock.patch('rally.cmd.commands.verify.open', create=True)
    @mock.patch('rally.db.verification_result_get')
    @mock.patch('rally.verification.verifiers.tempest.json2html.main',
                return_value='')
    def test_results_with_output_html_and_output_file(self,
                                                      mock_json2html_main,
                                                      mock_db_result_get,
                                                      mock_open):
        mock_open.return_value = mock.MagicMock()
        verification_uuid = '7140dd59-3a7b-41fd-a3ef-5e3e615d7dfa'
        fake_data = {}
        results = {'data': fake_data}
        mock_db_result_get.return_value = results
        self.verify.results(verification_uuid, output_html=True,
                            output_file='results')

        mock_db_result_get.assert_called_once_with(verification_uuid)
        mock_json2html_main.assert_called_once_with(fake_data)
        mock_open.assert_called_once_with('results', 'wb')
        fake_file = mock_open.return_value.__enter__.return_value
        fake_file.write.assert_called_once_with('')
