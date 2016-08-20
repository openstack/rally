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

BASE = "rally.plugins.openstack.scenarios.designate.basic"


class DesignateBasicTestCase(test.ScenarioTestCase):

    @mock.patch("%s.CreateAndListDomains._list_domains" % BASE)
    @mock.patch("%s.CreateAndListDomains._create_domain" % BASE)
    def test_create_and_list_domains(self,
                                     mock__create_domain,
                                     mock__list_domains):
        basic.CreateAndListDomains(self.context).run()
        mock__create_domain.assert_called_once_with()
        mock__list_domains.assert_called_once_with()

    @mock.patch("%s.CreateAndDeleteDomain._delete_domain" % BASE)
    @mock.patch("%s.CreateAndDeleteDomain._create_domain" % BASE,
                return_value={"id": "123"})
    def test_create_and_delete_domain(self,
                                      mock__create_domain,
                                      mock__delete_domain):

        basic.CreateAndDeleteDomain(self.context).run()

        mock__create_domain.assert_called_once_with()
        mock__delete_domain.assert_called_once_with("123")

    @mock.patch("%s.CreateAndUpdateDomain._update_domain" % BASE)
    @mock.patch("%s.CreateAndUpdateDomain._create_domain" % BASE)
    def test_create_and_update_domain(self,
                                      mock__create_domain,
                                      mock__update_domain):
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock__create_domain.return_value = domain
        basic.CreateAndUpdateDomain(self.context).run()
        mock__update_domain.assert_called_once_with(domain)

    @mock.patch("%s.ListDomains._list_domains" % BASE)
    def test_list_domains(self, mock__list_domains):
        basic.ListDomains(self.context).run()
        mock__list_domains.assert_called_once_with()

    @mock.patch("%s.CreateAndListRecords._list_records" % BASE)
    @mock.patch("%s.CreateAndListRecords._create_record" % BASE)
    @mock.patch("%s.CreateAndListRecords._create_domain" % BASE)
    def test_create_and_list_records(self,
                                     mock__create_domain,
                                     mock__create_record,
                                     mock__list_records):
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock__create_domain.return_value = domain
        records_per_domain = 5

        basic.CreateAndListRecords(self.context).run(
            records_per_domain=records_per_domain)
        mock__create_domain.assert_called_once_with()
        self.assertEqual(mock__create_record.mock_calls,
                         [mock.call(domain, atomic_action=False)]
                         * records_per_domain)
        mock__list_records.assert_called_once_with(domain["id"])

    @mock.patch("%s.CreateAndDeleteRecords._delete_record" % BASE)
    @mock.patch("%s.CreateAndDeleteRecords._create_record" % BASE)
    @mock.patch("%s.CreateAndDeleteRecords._create_domain" % BASE)
    def test_create_and_delete_records(self,
                                       mock__create_domain,
                                       mock__create_record,
                                       mock__delete_record):
        domain = {
            "name": "zone.name",
            "email": "email@zone.name",
            "id": "123"}
        mock__create_domain.return_value = domain
        mock__create_record.return_value = {"id": "321"}
        records_per_domain = 5

        basic.CreateAndDeleteRecords(self.context).run(
            records_per_domain=records_per_domain)
        mock__create_domain.assert_called_once_with()
        self.assertEqual(mock__create_record.mock_calls,
                         [mock.call(domain, atomic_action=False)]
                         * records_per_domain)
        self.assertEqual(mock__delete_record.mock_calls,
                         [mock.call(domain["id"],
                                    "321",
                                    atomic_action=False)]
                         * records_per_domain)

    @mock.patch("%s.ListRecords._list_records" % BASE)
    def test_list_records(self, mock__list_records):
        basic.ListRecords(self.context).run("123")
        mock__list_records.assert_called_once_with("123")

    @mock.patch("%s.CreateAndListServers._list_servers" % BASE)
    @mock.patch("%s.CreateAndListServers._create_server" % BASE)
    def test_create_and_list_servers(self,
                                     mock__create_server,
                                     mock__list_servers):
        basic.CreateAndListServers(self.context).run()

        mock__create_server.assert_called_once_with()
        mock__list_servers.assert_called_once_with()

    @mock.patch("%s.CreateAndDeleteServer._delete_server" % BASE)
    @mock.patch("%s.CreateAndDeleteServer._create_server" % BASE,
                return_value={"id": "123"})
    def test_create_and_delete_server(self,
                                      mock__create_server,
                                      mock__delete_server):
        basic.CreateAndDeleteServer(self.context).run()

        mock__create_server.assert_called_once_with()
        mock__delete_server.assert_called_once_with("123")

    @mock.patch("%s.ListServers._list_servers" % BASE)
    def test_list_servers(self, mock__list_servers):
        basic.ListServers(self.context).run()
        mock__list_servers.assert_called_once_with()

    # NOTE: API V2
    @mock.patch("%s.CreateAndListZones._list_zones" % BASE)
    @mock.patch("%s.CreateAndListZones._create_zone" % BASE)
    def test_create_and_list_zones(self,
                                   mock__create_zone,
                                   mock__list_zones):
        basic.CreateAndListZones(self.context).run()
        mock__create_zone.assert_called_once_with()
        mock__list_zones.assert_called_once_with()

    @mock.patch("%s.CreateAndDeleteZone._delete_zone" % BASE)
    @mock.patch("%s.CreateAndDeleteZone._create_zone" % BASE,
                return_value={"id": "123"})
    def test_create_and_delete_zone(self,
                                    mock__create_zone,
                                    mock__delete_zone):
        basic.CreateAndDeleteZone(self.context).run()

        mock__create_zone.assert_called_once_with()
        mock__delete_zone.assert_called_once_with("123")

    @mock.patch("%s.ListZones._list_zones" % BASE)
    def test_list_zones(self, mock_list_zones__list_zones):
        basic.ListZones(self.context).run()
        mock_list_zones__list_zones.assert_called_once_with()

    @mock.patch("%s.ListRecordsets._list_recordsets" % BASE)
    def test_list_recordsets(self, mock__list_recordsets):
        basic.ListRecordsets(self.context).run("123")
        mock__list_recordsets.assert_called_once_with("123")

    @mock.patch("%s.CreateAndDeleteRecordsets._delete_recordset" % BASE)
    @mock.patch("%s.CreateAndDeleteRecordsets._create_recordset" % BASE,
                return_value={"id": "321"})
    def test_create_and_delete_recordsets(self,
                                          mock__create_recordset,
                                          mock__delete_recordset):
        zone = {"id": "1234"}
        self.context.update({
            "tenant": {
                "zones": [zone]
            }
        })

        recordsets_per_zone = 5

        basic.CreateAndDeleteRecordsets(self.context).run(
            recordsets_per_zone=recordsets_per_zone)
        self.assertEqual(mock__create_recordset.mock_calls,
                         [mock.call(zone, atomic_action=False)]
                         * recordsets_per_zone)
        self.assertEqual(mock__delete_recordset.mock_calls,
                         [mock.call(zone["id"],
                                    "321",
                                    atomic_action=False)]
                         * recordsets_per_zone)

    @mock.patch("%s.CreateAndListRecordsets._list_recordsets" % BASE)
    @mock.patch("%s.CreateAndListRecordsets._create_recordset" % BASE)
    def test_create_and_list_recordsets(self,
                                        mock__create_recordset,
                                        mock__list_recordsets):
        zone = {"id": "1234"}
        self.context.update({
            "tenant": {
                "zones": [zone]
            }
        })
        recordsets_per_zone = 5

        basic.CreateAndListRecordsets(self.context).run(
            recordsets_per_zone=recordsets_per_zone)
        self.assertEqual(mock__create_recordset.mock_calls,
                         [mock.call(zone, atomic_action=False)]
                         * recordsets_per_zone)
        mock__list_recordsets.assert_called_once_with(zone["id"])
