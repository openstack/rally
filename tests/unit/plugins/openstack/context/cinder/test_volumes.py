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

import ddt
import mock

from rally.plugins.openstack.context.cinder import volumes
from rally.task import context
from tests.unit import test

CTX = "rally.plugins.openstack.context"
SERVICE = "rally.plugins.openstack.services.storage"


@ddt.ddt
class VolumeGeneratorTestCase(test.ScenarioTestCase):

    def _gen_tenants(self, count):
        tenants = {}
        for id_ in range(count):
            tenants[str(id_)] = {"name": str(id_)}
        return tenants

    def test_init(self):
        self.context.update({
            "config": {
                "volumes": {
                    "size": 1,
                    "volumes_per_tenant": 5,
                }
            }
        })

        inst = volumes.VolumeGenerator(self.context)
        self.assertEqual(inst.config, self.context["config"]["volumes"])

    @ddt.data({"config": {"size": 1, "volumes_per_tenant": 5}},
              {"config": {"size": 1, "type": None, "volumes_per_tenant": 5}},
              {"config": {"size": 1, "type": -1, "volumes_per_tenant": 5},
               "valid": False})
    @ddt.unpack
    @mock.patch("%s.block.BlockStorage" % SERVICE)
    def test_setup(self, mock_block_storage, config, valid=True):
        results = context.Context.validate("volumes", None, None, config)
        if valid:
            self.assertEqual([], results)
        else:
            self.assertEqual(1, len(results))

        from rally.plugins.openstack.services.storage import block
        created_volume = block.Volume(id="uuid", size=config["size"],
                                      name="vol", status="avaiable")

        mock_service = mock_block_storage.return_value
        mock_service.create_volume.return_value = created_volume
        users_per_tenant = 5
        volumes_per_tenant = config.get("volumes_per_tenant", 5)
        tenants = self._gen_tenants(2)
        users = []
        for id_ in tenants:
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "credential": mock.MagicMock()})

        self.context.update({
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": config
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        new_context = copy.deepcopy(self.context)
        for id_ in tenants.keys():
            new_context["tenants"][id_].setdefault("volumes", [])
            for i in range(volumes_per_tenant):
                new_context["tenants"][id_]["volumes"].append(
                    mock_service.create_volume.return_value._as_dict())

        volumes_ctx = volumes.VolumeGenerator(self.context)
        volumes_ctx.setup()
        self.assertEqual(new_context, self.context)

    @mock.patch("%s.cinder.volumes.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup):
        tenants_count = 2
        users_per_tenant = 5
        volumes_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "credential": "credential"})
            tenants[id_].setdefault("volumes", [])
            for j in range(volumes_per_tenant):
                tenants[id_]["volumes"].append({"id": "uuid"})

        self.context.update({
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": {
                    "size": 1,
                    "volumes_per_tenant": 5,
                }
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        volumes_ctx = volumes.VolumeGenerator(self.context)
        volumes_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["cinder.volumes"], users=self.context["users"],
            api_versions=None, superclass=volumes_ctx.__class__,
            task_id=self.context["owner_id"])

    @mock.patch("%s.cinder.volumes.resource_manager.cleanup" % CTX)
    def test_cleanup_api_versions(self, mock_cleanup):

        tenants_count = 2
        users_per_tenant = 5
        volumes_per_tenant = 5

        tenants = self._gen_tenants(tenants_count)
        users = []
        for id_ in tenants.keys():
            for i in range(users_per_tenant):
                users.append({"id": i, "tenant_id": id_,
                              "credential": "credential"})
            tenants[id_].setdefault("volumes", [])
            for j in range(volumes_per_tenant):
                tenants[id_]["volumes"].append({"id": "uuid"})

        api_version = {
            "cinder": {
                "version": 1,
                "service_type": "volume"
            }
        }
        self.context.update({
            "config": {
                "users": {
                    "tenants": 2,
                    "users_per_tenant": 5,
                    "concurrent": 10,
                },
                "volumes": {
                    "size": 1,
                    "type": "volume_type",
                    "volumes_per_tenant": 5,
                },
                "api_versions": api_version
            },
            "admin": {
                "credential": mock.MagicMock()
            },
            "users": users,
            "tenants": tenants
        })

        volumes_ctx = volumes.VolumeGenerator(self.context)
        volumes_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["cinder.volumes"],
            users=self.context["users"],
            api_versions=api_version,
            superclass=volumes_ctx.__class__,
            task_id=self.context["owner_id"])
