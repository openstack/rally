# Copyright 2016 IBM Corp.
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

from rally.plugins.openstack.scenarios.nova import agents
from tests.unit import test


class NovaAgentsTestCase(test.TestCase):

    def test_list_agents(self):
        scenario = agents.NovaAgents()
        scenario._list_agents = mock.Mock()
        scenario.list_agents(hypervisor=None)
        scenario._list_agents.assert_called_once_with(None)
