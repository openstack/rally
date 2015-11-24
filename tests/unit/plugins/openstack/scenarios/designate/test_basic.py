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

from rally.plugins.openstack.scenarios.designate import basic
from tests.unit import test

DESIGNATE_BASIC = ("rally.plugins.openstack.scenarios.designate.basic"
                   ".DesignateBasic")


class DesignateBasicTestCase(test.ScenarioTestCase):
    @mock.patch(DESIGNATE_BASIC + "._list_domains")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_list_domains(self, mock_designate_basic__create_domain,
                                     mock_designate_basic__list_domains):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.create_and_list_domains()
        mock_designate_basic__create_domain.assert_called_once_with()
        mock_designate_basic__list_domains.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._delete_domain")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_delete_domain(
            self, mock_designate_basic__create_domain,
            mock_designate_basic__delete_domain):

        scenario = basic.DesignateBasic(self.context)

        mock_designate_basic__create_domain.return_value = {"id": "123"}

        # Default options
        scenario.create_and_delete_domain()

        mock_designate_basic__create_domain.assert_called_once_with()
        mock_designate_basic__delete_domain.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._update_domain")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_update_domain(
            self, mock_designate_basic__create_domain,
            mock_designate_basic__update_domain):

        scenario = basic.DesignateBasic(self.context)
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock_designate_basic__create_domain.return_value = domain
        scenario.create_and_update_domain()
        mock_designate_basic__update_domain.assert_called_once_with(domain)

    @mock.patch(DESIGNATE_BASIC + "._list_domains")
    def test_list_domains(self, mock_designate_basic__list_domains):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.list_domains()
        mock_designate_basic__list_domains.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._list_records")
    @mock.patch(DESIGNATE_BASIC + "._create_record")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_list_records(
            self, mock_designate_basic__create_domain,
            mock_designate_basic__create_record,
            mock_designate_basic__list_records):
        scenario = basic.DesignateBasic(self.context)
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock_designate_basic__create_domain.return_value = domain
        records_per_domain = 5

        scenario.create_and_list_records(
            records_per_domain=records_per_domain)
        mock_designate_basic__create_domain.assert_called_once_with()
        self.assertEqual(
            mock_designate_basic__create_record.mock_calls,
            [mock.call(domain, atomic_action=False)]
            * records_per_domain)
        mock_designate_basic__list_records.assert_called_once_with(
            domain["id"])

    @mock.patch(DESIGNATE_BASIC + "._delete_record")
    @mock.patch(DESIGNATE_BASIC + "._create_record")
    @mock.patch(DESIGNATE_BASIC + "._create_domain")
    def test_create_and_delete_records(
            self, mock_designate_basic__create_domain,
            mock_designate_basic__create_record,
            mock_designate_basic__delete_record):
        scenario = basic.DesignateBasic(self.context)
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock_designate_basic__create_domain.return_value = domain
        mock_designate_basic__create_record.return_value = {"id": "321"}
        records_per_domain = 5

        scenario.create_and_delete_records(
            records_per_domain=records_per_domain)
        mock_designate_basic__create_domain.assert_called_once_with()
        self.assertEqual(
            mock_designate_basic__create_record.mock_calls,
            [mock.call(domain, atomic_action=False)]
            * records_per_domain)
        self.assertEqual(
            mock_designate_basic__delete_record.mock_calls,
            [mock.call(domain["id"], "321", atomic_action=False)]
            * records_per_domain)

    @mock.patch(DESIGNATE_BASIC + "._list_records")
    def test_list_records(self, mock_designate_basic__list_records):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.list_records("123")
        mock_designate_basic__list_records.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._list_servers")
    @mock.patch(DESIGNATE_BASIC + "._create_server")
    def test_create_and_list_servers(
            self, mock_designate_basic__create_server,
            mock_designate_basic__list_servers):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.create_and_list_servers()
        mock_designate_basic__create_server.assert_called_once_with()
        mock_designate_basic__list_servers.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._delete_server")
    @mock.patch(DESIGNATE_BASIC + "._create_server")
    def test_create_and_delete_server(
            self, mock_designate_basic__create_server,
            mock_designate_basic__delete_server):
        scenario = basic.DesignateBasic(self.context)

        mock_designate_basic__create_server.return_value = {"id": "123"}

        # Default options
        scenario.create_and_delete_server()

        mock_designate_basic__create_server.assert_called_once_with()
        mock_designate_basic__delete_server.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._list_servers")
    def test_list_servers(self, mock_designate_basic__list_servers):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.list_servers()
        mock_designate_basic__list_servers.assert_called_once_with()

    # NOTE: API V2
    @mock.patch(DESIGNATE_BASIC + "._list_zones")
    @mock.patch(DESIGNATE_BASIC + "._create_zone")
    def test_create_and_list_zones(self, mock_designate_basic__create_zone,
                                   mock_designate_basic__list_zones):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.create_and_list_zones()
        mock_designate_basic__create_zone.assert_called_once_with()
        mock_designate_basic__list_zones.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._delete_zone")
    @mock.patch(DESIGNATE_BASIC + "._create_zone")
    def test_create_and_delete_zone(
            self, mock_designate_basic__create_zone,
            mock_designate_basic__delete_zone):

        scenario = basic.DesignateBasic(self.context)

        mock_designate_basic__create_zone.return_value = {"id": "123"}

        # Default options
        scenario.create_and_delete_zone()

        mock_designate_basic__create_zone.assert_called_once_with()
        mock_designate_basic__delete_zone.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._list_zones")
    def test_list_zones(self, mock_designate_basic__list_zones):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.list_zones()
        mock_designate_basic__list_zones.assert_called_once_with()

    @mock.patch(DESIGNATE_BASIC + "._list_recordsets")
    def test_list_recordsets(self, mock_designate_basic__list_recordsets):
        scenario = basic.DesignateBasic(self.context)

        # Default options
        scenario.list_recordsets("123")
        mock_designate_basic__list_recordsets.assert_called_once_with("123")

    @mock.patch(DESIGNATE_BASIC + "._delete_recordset")
    @mock.patch(DESIGNATE_BASIC + "._create_recordset")
    def test_create_and_delete_recordsets(
            self, mock_designate_basic__create_recordset,
            mock_designate_basic__delete_recordset):
        zone = {"id": "1234"}
        self.context.update({
            "tenant": {
                "zones": [zone]
            }
        })

        scenario = basic.DesignateBasic(self.context)
        mock_designate_basic__create_recordset.return_value = {"id": "321"}
        recordsets_per_zone = 5

        scenario.create_and_delete_recordsets(
            recordsets_per_zone=recordsets_per_zone)
        self.assertEqual(
            mock_designate_basic__create_recordset.mock_calls,
            [mock.call(zone, atomic_action=False)]
            * recordsets_per_zone)
        self.assertEqual(
            mock_designate_basic__delete_recordset.mock_calls,
            [mock.call(zone["id"], "321", atomic_action=False)]
            * recordsets_per_zone)

    @mock.patch(DESIGNATE_BASIC + "._list_recordsets")
    @mock.patch(DESIGNATE_BASIC + "._create_recordset")
    def test_create_and_list_recordsets(
            self, mock_designate_basic__create_recordset,
            mock_designate_basic__list_recordsets):
        zone = {"id": "1234"}
        self.context.update({
            "tenant": {
                "zones": [zone]
            }
        })
        scenario = basic.DesignateBasic(self.context)
        recordsets_per_zone = 5

        scenario.create_and_list_recordsets(
            recordsets_per_zone=recordsets_per_zone)
        self.assertEqual(
            mock_designate_basic__create_recordset.mock_calls,
            [mock.call(zone, atomic_action=False)]
            * recordsets_per_zone)
        mock_designate_basic__list_recordsets.assert_called_once_with(
            zone["id"])
