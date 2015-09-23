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

from rally.plugins.openstack.scenarios.designate import utils
from tests.unit import test

DESIGNATE_UTILS = "rally.plugins.openstack.scenarios.designate.utils."


class DesignateScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(DesignateScenarioTestCase, self).setUp()
        self.domain = mock.Mock()
        self.server = mock.Mock()

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_domain(self, mock_generate_random_name):
        scenario = utils.DesignateScenario()

        random_name = "foo"
        explicit_name = "bar.io."
        email = "root@zone.name"

        mock_generate_random_name.return_value = random_name
        scenario = utils.DesignateScenario(context=self.context)
        self.clients("designate").domains.create.return_value = self.domain

        # Check that the defaults / randoms are used if nothing is specified
        domain = scenario._create_domain()
        self.clients("designate").domains.create.assert_called_once_with(
            {"email": "root@random.name", "name": "%s.name." % random_name})
        self.assertEqual(self.domain, domain)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_domain")

        self.clients("designate").domains.create.reset_mock()

        # Check that when specifying zone defaults are not used...
        data = {"email": email, "name": explicit_name}
        domain = scenario._create_domain(data)
        self.clients("designate").domains.create.assert_called_once_with(data)
        self.assertEqual(self.domain, domain)

    def test_list_domains(self):
        scenario = utils.DesignateScenario(context=self.context)
        return_domains_list = scenario._list_domains()
        self.assertEqual(self.clients("designate").domains.list.return_value,
                         return_domains_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.list_domains")

    def test_delete_domain(self):
        scenario = utils.DesignateScenario(context=self.context)

        domain = scenario._create_domain()
        scenario._delete_domain(domain["id"])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.delete_domain")

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_record(self, mock_generate_random_name):
        scenario = utils.DesignateScenario()

        random_name = "foo"
        domain_name = "zone.name."
        random_record_name = "%s.%s" % (random_name, domain_name)

        mock_generate_random_name.return_value = random_name
        scenario = utils.DesignateScenario(context=self.context)

        domain = {"name": domain_name, "id": "123"}

        # Create with randoms (name and type)
        scenario._create_record(domain)
        self.clients("designate").records.create.assert_called_once_with(
            domain["id"],
            {"name": random_record_name, "type": "A", "data": "10.0.0.1"})

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_record")

        self.clients("designate").records.create.reset_mock()

        # Specify name
        record = {"name": "www.zone.name.", "type": "ASD"}
        scenario._create_record(domain, record)
        self.clients("designate").records.create.assert_called_once_with(
            domain["id"], record)

    def test_list_records(self):
        scenario = utils.DesignateScenario(context=self.context)
        return_records_list = scenario._list_records("123")
        self.assertEqual(self.clients("designate").records.list.return_value,
                         return_records_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.list_records")

    def test_delete_record(self):
        scenario = utils.DesignateScenario(context=self.context)

        domain_id = mock.Mock()
        record_id = mock.Mock()
        scenario._delete_record(domain_id, record_id)
        self.clients("designate").records.delete.assert_called_once_with(
            domain_id, record_id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.delete_record")

        self.clients("designate").records.delete.reset_mock()
        scenario._delete_record(domain_id, record_id, atomic_action=False)
        self.clients("designate").records.delete.assert_called_once_with(
            domain_id, record_id)

    @mock.patch("rally.common.utils.generate_random_name")
    def test_create_server(self, mock_generate_random_name):
        scenario = utils.DesignateScenario(context=self.context)

        random_name = "foo"
        explicit_name = "bar.io."

        mock_generate_random_name.return_value = random_name
        self.admin_clients(
            "designate").servers.create.return_value = self.server

        # Check that the defaults / randoms are used if nothing is specified
        server = scenario._create_server()
        self.admin_clients("designate").servers.create.assert_called_once_with(
            {"name": "name.%s." % random_name})
        self.assertEqual(self.server, server)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_server")

        self.admin_clients("designate").servers.create.reset_mock()

        # Check that when specifying server name defaults are not used...
        data = {"name": explicit_name}
        server = scenario._create_server(data)
        self.admin_clients(
            "designate").servers.create.assert_called_once_with(data)
        self.assertEqual(self.server, server)

    def test_delete_server(self):
        scenario = utils.DesignateScenario(context=self.context)

        scenario._delete_server("foo_id")
        self.admin_clients("designate").servers.delete.assert_called_once_with(
            "foo_id")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.delete_server")
