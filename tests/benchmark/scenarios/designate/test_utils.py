# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Author: Endre Karlson <endre.karlson@hp.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.benchmark.scenarios.designate import utils
from tests.benchmark.scenarios import test_base
from tests import test


DESIGNATE_UTILS = "rally.benchmark.scenarios.designate.utils."


class DesignateScenarioTestCase(test.TestCase):

    def setUp(self):
        super(DesignateScenarioTestCase, self).setUp()
        self.domain = mock.Mock()

    def _test_atomic_action_timer(self, atomic_actions_time, name):
        action_duration = test_base.get_atomic_action_timer_value_by_name(
            atomic_actions_time, name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    @mock.patch(DESIGNATE_UTILS + 'DesignateScenario._generate_random_name')
    @mock.patch(DESIGNATE_UTILS + 'DesignateScenario.clients')
    def test_create_domain(self, mock_clients, mock_random_name):
        scenario = utils.DesignateScenario()

        random_name = "foo"
        explicit_name = "bar.io."
        email = "root@zone.name"

        mock_random_name.return_value = random_name
        mock_clients("designate").domains.create.return_value = self.domain

        # Check that the defaults / randoms are used if nothing is specified
        domain = scenario._create_domain()
        mock_clients("designate").domains.create.assert_called_once_with(
            {"email": "root@random.name", "name": '%s.name.' % random_name})
        self.assertEqual(self.domain, domain)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'designate.create_domain')

        mock_clients("designate").domains.create.reset_mock()

        # Check that when specifying zone defaults are not used...
        data = {"email": email, "name": explicit_name}
        domain = scenario._create_domain(data)
        mock_clients("designate").domains.create.assert_called_once_with(data)
        self.assertEqual(self.domain, domain)

    @mock.patch(DESIGNATE_UTILS + 'DesignateScenario.clients')
    def test_list_domains(self, mock_clients):
        scenario = utils.DesignateScenario()
        domains_list = []
        mock_clients("designate").domains.list.return_value = domains_list
        return_domains_list = scenario._list_domains()
        self.assertEqual(domains_list, return_domains_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'designate.list_domains')

    @mock.patch(DESIGNATE_UTILS + 'DesignateScenario.clients')
    def test_delete_domain(self, mock_clients):
        scenario = utils.DesignateScenario()

        domain = scenario._create_domain()
        scenario._delete_domain(domain['id'])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'designate.delete_domain')
