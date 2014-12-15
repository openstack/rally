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

    def _gen_tenants(self, count):
        tenants = dict()
        for id in range(count):
            tenants[str(id)] = dict(name=str(id))
        return tenants

    def test_init(self):
        context = {}
        context["task"] = mock.MagicMock()
        context["config"] = {
            "volumes": {
                "size": 1,
            }
        }

        inst = volumes.VolumeGenerator(context)
        self.assertEqual(inst.config, context["config"]["volumes"])

    @mock.patch("%s.cinder.utils.CinderScenario._create_volume" % SCN,
                return_value=fakes.FakeVolume(id="uuid"))
    @mock.patch("%s.volumes.osclients" % CTX)
    def test_setup(self, mock_osclients, mock_volume_create):
        fc = fakes.FakeClients()
        mock_osclients.Clients.return_value = fc

        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = list()
        for id in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": "endpoint"})

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
            "users": users,
            "tenants": tenants
        }

        new_context = copy.deepcopy(real_context)
        for id in tenants.keys():
            new_context["tenants"][id]["volume"] = "uuid"

        volumes_ctx = volumes.VolumeGenerator(real_context)
        volumes_ctx.setup()
        self.assertEqual(new_context, real_context)

    @mock.patch("%s.volumes.osclients" % CTX)
    @mock.patch("%s.volumes.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_osclients):

        tenants_count = 2
        users_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = list()
        for id in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id,
                              "endpoint": "endpoint"})
            tenants[id]["volume"] = "uuid"

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
            "users": users,
            "tenants": tenants
        }

        volumes_ctx = volumes.VolumeGenerator(context)
        volumes_ctx.cleanup()

        mock_cleanup.assert_called_once_with(names=["cinder.volumes"],
                                             users=context["users"])
