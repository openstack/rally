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
from tests.unit import test

import mock


class AuthenticateTestCase(test.ScenarioTestCase):

    def test_keystone(self):
        scenario_inst = authenticate.Keystone()
        scenario_inst.run()
        self.assertTrue(self.client_created("keystone"))
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.keystone")

    def test_validate_glance(self):
        scenario_inst = authenticate.ValidateGlance()
        scenario_inst.run(5)

        # NOTE(stpierre): We can't use assert_has_calls() here because
        # that includes calls on the return values of the mock object
        # as well. Glance (and Heat and Monasca, tested below) returns
        # an iterator that the scenario wraps in list() in order to
        # force glanceclient to actually make the API call, and this
        # results in a bunch of call().__iter__() and call().__len__()
        # calls that aren't matched if we use assert_has_calls().
        self.assertItemsEqual(
            self.clients("glance").images.list.call_args_list,
            [mock.call(name=mock.ANY)] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_glance_5_times")

    def test_validate_nova(self):
        scenario_inst = authenticate.ValidateNova()
        scenario_inst.run(5)
        self.clients("nova").flavors.list.assert_has_calls([mock.call()] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_nova_5_times")

    def test_validate_ceilometer(self):
        scenario_inst = authenticate.ValidateCeilometer()
        scenario_inst.run(5)
        self.clients("ceilometer").meters.list.assert_has_calls(
            [mock.call()] * 5)
        self._test_atomic_action_timer(
            scenario_inst.atomic_actions(),
            "authenticate.validate_ceilometer_5_times")

    def test_validate_cinder(self):
        scenario_inst = authenticate.ValidateCinder()
        scenario_inst.run(5)
        self.clients("cinder").volume_types.list.assert_has_calls(
            [mock.call()] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_cinder_5_times")

    def test_validate_neutron(self):
        scenario_inst = authenticate.ValidateNeutron()
        scenario_inst.run(5)
        self.clients("neutron").list_networks.assert_has_calls(
            [mock.call()] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_neutron_5_times")

    def test_validate_heat(self):
        scenario_inst = authenticate.ValidateHeat()
        scenario_inst.run(5)
        self.assertItemsEqual(
            self.clients("heat").stacks.list.call_args_list,
            [mock.call(limit=0)] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_heat_5_times")

    def test_validate_monasca(self):
        scenario_inst = authenticate.ValidateMonasca()
        scenario_inst.run(5)
        self.assertItemsEqual(
            self.clients("monasca").metrics.list.call_args_list,
            [mock.call(limit=0)] * 5)
        self._test_atomic_action_timer(scenario_inst.atomic_actions(),
                                       "authenticate.validate_monasca_5_times")
