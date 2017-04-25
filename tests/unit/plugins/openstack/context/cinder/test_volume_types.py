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

import mock

from rally.plugins.openstack.context.cinder import volume_types
from tests.unit import test

CTX = "rally.plugins.openstack.context.cinder.volume_types"
SERVICE = "rally.plugins.openstack.services.storage"


class VolumeTypeGeneratorTestCase(test.ContextTestCase):
    def setUp(self):
        super(VolumeTypeGeneratorTestCase, self).setUp()
        self.context.update({"admin": {"credential": "admin_creds"}})

    @mock.patch("%s.block.BlockStorage" % SERVICE)
    def test_setup(self, mock_block_storage):
        self.context.update({"config": {"volume_types": ["foo", "bar"]}})
        mock_service = mock_block_storage.return_value
        mock_service.create_volume_type.side_effect = (
            mock.Mock(id="foo-id"), mock.Mock(id="bar-id"))

        vtype_ctx = volume_types.VolumeTypeGenerator(self.context)
        vtype_ctx.setup()

        mock_service.create_volume_type.assert_has_calls(
            [mock.call("foo"), mock.call("bar")])
        self.assertEqual(self.context["volume_types"],
                         [{"id": "foo-id", "name": "foo"},
                          {"id": "bar-id", "name": "bar"}])

    @mock.patch("%s.utils.make_name_matcher" % CTX)
    @mock.patch("%s.resource_manager.cleanup" % CTX)
    def test_cleanup(self, mock_cleanup, mock_make_name_matcher):
        self.context.update({
            "config": {"volume_types": ["foo", "bar"],
                       "api_versions": {
                           "cinder": {"version": 2,
                                      "service_type": "volumev2"}}}})

        vtype_ctx = volume_types.VolumeTypeGenerator(self.context)

        vtype_ctx.cleanup()

        mock_cleanup.assert_called_once_with(
            names=["cinder.volume_types"],
            admin=self.context["admin"],
            api_versions=self.context["config"]["api_versions"],
            superclass=mock_make_name_matcher.return_value,
            task_id=vtype_ctx.get_owner_id())

        mock_make_name_matcher.assert_called_once_with("foo", "bar")
