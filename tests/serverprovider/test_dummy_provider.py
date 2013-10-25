# Copyright 2013: Mirantis Inc.
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

from rally import serverprovider
from rally import test


ProviderFactory = serverprovider.ProviderFactory


class DummyProviderTestCase(test.TestCase):

    def test_create_vms(self):
        config = {'name': 'DummyProvider',
                  'credentials': ['user@host1', 'user@host2']}
        provider = serverprovider.ProviderFactory.get_provider(config, None)
        credentials = provider.create_vms()
        self.assertEqual(['host1', 'host2'], [s.ip for s in credentials])
        self.assertEqual(['user', 'user'], [s.user for s in credentials])
