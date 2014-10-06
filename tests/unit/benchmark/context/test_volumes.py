# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import copy

import mock

from rally.benchmark.context import volumes
from tests.unit import fakes
from tests.unit import test

CTX = "rally.benchmark.context"
SCN = "rally.benchmark.scenarios"


class VolumeGeneratorTestCase(test.TestCase):
    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "volumes": {
                "size": 1,
            }
        }

        new_context = copy.deepcopy(context)
        new_context["volumes"] = []
        volumes.VolumeGenerator(context)
        self.assertEqual(new_context, context)

    @mock.patch("%s.cinder.utils.CinderScenario._create_volume" % SCN,
                return_value=fakes.FakeVolume(id="uuid"))
    @mock.patch("%s.volumes.osclients" % CTX)
    def test_setup(self, mock_osclients, mock_volume_create):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        ctx_volumes = [
            {'volume_id': 'uuid', 'endpoint': 'endpoint', 'tenant_id': i}
            for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

        real_context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": {
                    "size": 1,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": user_key,
        }

        new_context = copy.deepcopy(real_context)
        new_context["volumes"] = ctx_volumes

        volumes_ctx = volumes.VolumeGenerator(real_context)
        volumes_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.volumes.osclients" % CTX)
    @mock.patch("%s.cleanup.utils.delete_cinder_resources" % CTX)
    def test_cleanup(self, mock_cinder_remover, mock_osclients):
        ctx_volumes = [
            {'volume_id': 'uuid', 'endpoint': mock.MagicMock(), 'tenant_id': i}
            for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

        context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": {
                    "size": 1,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": user_key,
            "volumes": ctx_volumes,
        }

        volumes_ctx = volumes.VolumeGenerator(context)
        volumes_ctx.cleanup()

        self.assertEqual(2, len(mock_cinder_remover.mock_calls))

    @mock.patch("%s.volumes.osclients" % CTX)
    @mock.patch("%s.cleanup.utils.delete_cinder_resources" % CTX)
    def test_cleanup_exception(self, mock_cinder_remover, mock_osclients):
        ctx_volumes = [
            {'volume_id': 'uuid', 'endpoint': mock.MagicMock(), 'tenant_id': i}
            for i in range(2)]
        user_key = [{'id': i, 'tenant_id': j, 'endpoint': 'endpoint'}
                    for j in range(2)
                    for i in range(5)]

        context = {
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": {
                    "size": 1,
                }
            },
            "admin": {
                "endpoint": mock.MagicMock()
            },
            "task": mock.MagicMock(),
            "users": user_key,
            "volumes": ctx_volumes,
        }

        mock_cinder_remover.side_effect = Exception()
        volumes_ctx = volumes.VolumeGenerator(context)
        volumes_ctx.cleanup()
        self.assertEqual(2, len(mock_cinder_remover.mock_calls))
