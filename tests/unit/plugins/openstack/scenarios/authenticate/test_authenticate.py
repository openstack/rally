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

from rally.plugins.openstack.scenarios.authenticate import authenticate
from rally.task import atomic
from tests.unit import test


AUTHENTICATE_MODULE = (
    "rally.plugins.openstack.scenarios.authenticate.authenticate")


class AuthenticateTestCase(test.ScenarioTestCase):

    def test_keystone(self):
        scenario_inst = authenticate.Authenticate()
        scenario_inst.keystone()
        self.assertTrue(self.client_created("keystone"))

    def test_validate_glance(self):
        scenario_inst = authenticate.Authenticate()
        image_name = "__intentionally_non_existent_image___"
        with atomic.ActionTimer(scenario_inst,
                                "authenticate.validate_glance"):
            scenario_inst.validate_glance(5)
        self.clients("glance").images.list.assert_called_with(name=image_name)
        self.assertEqual(self.clients("glance").images.list.call_count, 5)

    def test_validate_nova(self):
        scenario_inst = authenticate.Authenticate()
        with atomic.ActionTimer(scenario_inst,
                                "authenticate.validate_nova"):
            scenario_inst.validate_nova(5)
        self.assertEqual(self.clients("nova").flavors.list.call_count, 5)

    def test_validate_cinder(self):
        scenario_inst = authenticate.Authenticate()
        with atomic.ActionTimer(scenario_inst,
                                "authenticate.validate_cinder"):
            scenario_inst.validate_cinder(5)
        self.assertEqual(self.clients("cinder").volume_types.list.call_count,
                         5)

    def test_validate_neutron(self):
        scenario_inst = authenticate.Authenticate()
        with atomic.ActionTimer(scenario_inst,
                                "authenticate.validate_neutron"):
            scenario_inst.validate_neutron(5)
        self.assertEqual(self.clients("neutron").list_networks.call_count, 5)

    def test_validate_heat(self):
        scenario_inst = authenticate.Authenticate()
        with atomic.ActionTimer(scenario_inst,
                                "authenticate.validate_heat"):
            scenario_inst.validate_heat(5)
        self.clients("heat").stacks.list.assert_called_with(limit=0)
        self.assertEqual(self.clients("heat").stacks.list.call_count, 5)
