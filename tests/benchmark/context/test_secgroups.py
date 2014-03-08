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

from rally.benchmark.context import secgroup
from tests import fakes
from tests import test


class SecGroupContextTestCase(test.TestCase):

    @mock.patch('rally.benchmark.context.secgroup.osclients.Clients')
    def test_prep_ssh_sec_group(self, mock_osclients):
        fake_nova = fakes.FakeNovaClient()
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_osclients.return_value = mock_cl

        secgroup._prepare_open_secgroup('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        self.assertTrue(
            secgroup.SSH_GROUP_NAME in
                [sg.name for sg in fake_nova.security_groups.list()]
        )

        # run prep again, check that another security group is not created
        secgroup._prepare_open_secgroup('endpoint')
        self.assertEqual(len(fake_nova.security_groups.list()), 2)

    @mock.patch('rally.benchmark.context.secgroup.osclients.Clients')
    def test_prep_ssh_sec_group_rules(self, mock_osclients):
        fake_nova = fakes.FakeNovaClient()

        #NOTE(hughsaunders) Default security group is precreated
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_cl = mock.MagicMock()
        mock_cl.nova.return_value = fake_nova
        mock_osclients.return_value = mock_cl

        secgroup._prepare_open_secgroup('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        rally_open = fake_nova.security_groups.find(secgroup.SSH_GROUP_NAME)
        self.assertEqual(len(rally_open.rules), 3)

        # run prep again, check that extra rules are not created
        secgroup._prepare_open_secgroup('endpoint')
        rally_open = fake_nova.security_groups.find(secgroup.SSH_GROUP_NAME)
        self.assertEqual(len(rally_open.rules), 3)
