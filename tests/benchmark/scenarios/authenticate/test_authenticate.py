# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

from rally.benchmark.scenarios.authenticate import authenticate
from tests import fakes
from tests import test


class AuthenticateTestCase(test.TestCase):

    @mock.patch("rally.osclients")
    def test_keystone(self, mock_osclients):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        scenario = authenticate.Authenticate(admin_clients=mock_osclients,
                                             clients=mock_osclients)

        scenario.keystone()
        self.assertEqual(scenario._clients.keystone.call_count, 1)
