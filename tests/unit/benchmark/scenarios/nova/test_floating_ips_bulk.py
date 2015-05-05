# Copyright 2015: Mirantis Inc.
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

from rally.benchmark.scenarios.nova import floating_ips_bulk
from tests.unit import test


class NovaFloatingIPsBulkTestCase(test.TestCase):

    def test_create_and_list_floating_ips_bulk(self):
        scenario = floating_ips_bulk.NovaFloatingIpsBulk()
        scenario._create_floating_ips_bulk = mock.MagicMock()
        scenario._list_floating_ips_bulk = mock.MagicMock()
        start_cidr = "10.2.0.0/24"
        scenario.create_and_list_floating_ips_bulk(start_cidr=start_cidr,
                                                   fakearg="fakearg")

        scenario._create_floating_ips_bulk.assert_called_once_with(
            start_cidr, fakearg="fakearg")
        scenario._list_floating_ips_bulk.assert_called_once_with()

    def test_create_and_delete_floating_ips_bulk(self):
        scenario = floating_ips_bulk.NovaFloatingIpsBulk()
        fake_floating_ips_bulk = mock.MagicMock()
        fake_floating_ips_bulk.ip_range = "10.2.0.0/24"
        scenario._create_floating_ips_bulk = mock.MagicMock(
            return_value=fake_floating_ips_bulk)
        scenario._delete_floating_ips_bulk = mock.MagicMock()
        start_cidr = "10.2.0.0/24"
        scenario.create_and_delete_floating_ips_bulk(start_cidr=start_cidr,
                                                     fakearg="fakearg")

        scenario._create_floating_ips_bulk.assert_called_once_with(
            start_cidr, fakearg="fakearg")
        scenario._delete_floating_ips_bulk.assert_called_once_with(
            fake_floating_ips_bulk.ip_range)
