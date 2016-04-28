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
from tests.unit import test


class DiscoverTestCase(test.TestCase):
    def test_discover_network_impl_based_on_service(self):

        class SomeService(service.UnifiedOpenStackService):
            pass

        @service.service("nova-network", "network", version="1",
                         client_name="nova")
        class NovaNetService(service.Service):
            pass

        @service.compat_layer(NovaNetService)
        class UnifiedNovaNetService(SomeService):
            @classmethod
            def is_applicable(cls, clients):
                return True

        @service.service("neutron", "network", version="2")
        class NeutronV2Service(service.Service):
            pass

        @service.compat_layer(NeutronV2Service)
        class UnifiedNeutronV2Service(SomeService):
            pass

        clients = mock.MagicMock()
        clients.nova.choose_version.return_value = "1"
        clients.neutron.choose_version.return_value = "2"

        clients.services.return_value = {}
        self.assertIsInstance(SomeService(clients)._impl,
                              UnifiedNovaNetService)

        clients.nova.return_value.services.list.reset_mock()

        clients.services.return_value = {"network": "neutron"}
        self.assertIsInstance(SomeService(clients)._impl,
                              UnifiedNeutronV2Service)
