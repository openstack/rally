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

import ddt
import mock

from rally.plugins.openstack.scenarios.designate import utils
from tests.unit import test

DESIGNATE_UTILS = "rally.plugins.openstack.scenarios.designate.utils."


@ddt.ddt
class DesignateScenarioTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(DesignateScenarioTestCase, self).setUp()
        self.domain = mock.Mock()
        self.zone = mock.Mock()
        self.server = mock.Mock()

        self.client = self.clients("designate", version="2")

    @ddt.data(
        {},
        {"email": "root@zone.name"})
    def test_create_domain(self, domain_data):
        random_name = "foo"
        scenario = utils.DesignateScenario(context=self.context)
        scenario.generate_random_name = mock.Mock(return_value=random_name)
        self.clients("designate").domains.create.return_value = self.domain
        expected = {"email": "root@random.name"}
        expected.update(domain_data)
        expected["name"] = "%s.name." % random_name

        domain = scenario._create_domain(domain_data)
        self.clients("designate").domains.create.assert_called_once_with(
            expected)
        self.assertEqual(self.domain, domain)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_domain")

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

    def test_update_domain(self):
        scenario = utils.DesignateScenario(context=self.context)
        domain = scenario._create_domain()
        self.clients("designate").domains.update.return_value = self.domain
        updated_domain = scenario._update_domain(domain)
        self.clients("designate").domains.update.assert_called_once_with(
            domain)
        self.assertEqual(self.domain, updated_domain)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.update_domain")

    @ddt.data(
        {},
        {"data": "127.0.0.1"})
    def test_create_record(self, record_data):
        random_name = "foo"
        domain_name = "zone.name."
        domain = {"name": domain_name, "id": "123"}
        record_name = "%s.%s" % (random_name, domain_name)

        scenario = utils.DesignateScenario(context=self.context)
        scenario.generate_random_name = mock.Mock(return_value=random_name)

        expected = {"type": "A", "data": "10.0.0.1"}
        expected.update(record_data)
        expected["name"] = record_name

        scenario._create_record(domain, record=record_data)
        self.clients("designate").records.create.assert_called_once_with(
            domain["id"], expected)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_record")

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

    def test_create_server(self):
        scenario = utils.DesignateScenario(context=self.context)
        random_name = "foo"
        scenario.generate_random_name = mock.Mock(return_value=random_name)

        explicit_name = "bar.io."

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

    # NOTE: API V2
    @ddt.data(
        {},
        {"email": "root@zone.name"},
        {"name": "example.name."},
        {
            "email": "root@zone.name",
            "name": "example.name."
        })
    def test_create_zone(self, zone_data):
        scenario = utils.DesignateScenario()

        random_name = "foo"

        scenario = utils.DesignateScenario(context=self.context)
        scenario.generate_random_name = mock.Mock(return_value=random_name)
        self.client.zones.create.return_value = self.zone

        expected = {
            "email": "root@random.name",
            "name": "%s.name." % random_name,
            "type_": "PRIMARY"
        }
        expected.update(zone_data)

        # Check that the defaults / randoms are used if nothing is specified
        zone = scenario._create_zone(**zone_data)
        self.client.zones.create.assert_called_once_with(
            description=None,
            ttl=None,
            **expected)
        self.assertEqual(self.zone, zone)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_zone")

    def test_list_zones(self):
        scenario = utils.DesignateScenario(context=self.context)
        return_zones_list = scenario._list_zones()
        self.assertEqual(self.client.zones.list.return_value,
                         return_zones_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.list_zones")

    def test_delete_zone(self):
        scenario = utils.DesignateScenario(context=self.context)

        zone = scenario._create_zone()
        scenario._delete_zone(zone["id"])
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.delete_zone")

    def test_list_recordsets(self):
        scenario = utils.DesignateScenario(context=self.context)
        return_recordsets_list = scenario._list_recordsets("123")
        self.assertEqual(
            self.client.recordsets.list.return_value,
            return_recordsets_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.list_recordsets")

    @ddt.data(
        {},
        {"data": "127.0.0.1"})
    def test_create_recordset(self, recordset_data):
        scenario = utils.DesignateScenario()

        random_name = "foo"
        zone_name = "zone.name."
        random_recordset_name = "%s.%s" % (random_name, zone_name)

        scenario = utils.DesignateScenario(context=self.context)
        scenario.generate_random_name = mock.Mock(return_value=random_name)

        zone = {"name": zone_name, "id": "123"}

        # Create with randoms (name and type)
        scenario._create_recordset(zone)

        self.client.recordsets.create.assert_called_once_with(
            zone["id"],
            name=random_recordset_name,
            type_="A",
            records=["10.0.0.1"])

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.create_recordset")

        self.client.recordsets.create.reset_mock()

        # Specify name
        recordset = {"name": "www.zone.name.", "type_": "ASD"}
        scenario._create_recordset(zone, recordset)
        self.client.recordsets.create.assert_called_once_with(
            zone["id"],
            name="www.zone.name.",
            type_="ASD",
            records=["10.0.0.1"])

        self.client.recordsets.create.reset_mock()

        # Specify type without underscore
        scenario._create_recordset(zone, {"type": "A"})
        self.client.recordsets.create.assert_called_once_with(
            zone["id"],
            name="foo.zone.name.",
            type_="A",
            records=["10.0.0.1"])

    def test_delete_recordset(self):
        scenario = utils.DesignateScenario(context=self.context)

        zone_id = mock.Mock()
        recordset_id = mock.Mock()
        scenario._delete_recordset(zone_id, recordset_id)
        self.client.recordsets.delete.assert_called_once_with(
            zone_id, recordset_id)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "designate.delete_recordset")

        self.client.recordsets.delete.reset_mock()
        scenario._delete_recordset(zone_id, recordset_id, atomic_action=False)
        self.client.recordsets.delete.assert_called_once_with(
            zone_id, recordset_id)
