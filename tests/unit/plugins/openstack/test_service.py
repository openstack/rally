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

from rally.plugins.openstack import service
from rally.task import service as base_service
from tests.unit import test


class DiscoverTestCase(test.TestCase):
    def test_discover_network_impl_based_on_service(self):

        class SomeService(base_service.UnifiedService):
            pass

        @service.service("neutron", "network", version="2")
        class NeutronV2Service(service.Service):
            pass

        @service.compat_layer(NeutronV2Service)
        class UnifiedNeutronV2Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.neutron.choose_version.return_value = "2"

        clients.services.return_value = {}

        clients.services.return_value = {"network": "neutron"}
        self.assertIsInstance(SomeService(clients)._impl,
                              UnifiedNeutronV2Service)
