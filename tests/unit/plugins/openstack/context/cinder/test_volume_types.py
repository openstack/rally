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

CTX = "rally.plugins.openstack.context"


class VolumeTypeGeneratorTestCase(test.ContextTestCase):
    def setUp(self):
        super(VolumeTypeGeneratorTestCase, self).setUp()
        self.context.update({"admin": {"credential": "admin_creds"}})

    def test_setup(self):
        self.context.update({"config": {"volume_types": ["foo", "bar"]}})
        create = self.clients("cinder",
                              admin=True).volume_types.create
        create.side_effect = (mock.Mock(id="foo-id"),
                              mock.Mock(id="bar-id"))

        vtype_ctx = volume_types.VolumeTypeGenerator(self.context)
        vtype_ctx.setup()

        create.assert_has_calls(
            [mock.call("foo"), mock.call("bar")])
        self.assertEqual(self.context["volume_types"],
                         [{"id": "foo-id", "name": "foo"},
                          {"id": "bar-id", "name": "bar"}])

    def test_cleanup(self):
        self.context.update({
            "config": {"volume_types": ["foo", "bar"]},
            "volume_types": [
                {"id": "foo_id", "name": "foo"},
                {"id": "bar_id", "name": "bar"}],
            "api_versions": {
                "cinder": {"version": 2, "service_type": "volumev2"}}})

        vtype_ctx = volume_types.VolumeTypeGenerator(self.context)
        vtype_ctx.cleanup()

        delete = self.clients("cinder",
                              admin=True).volume_types.delete
        delete.assert_has_calls(
            [mock.call("foo_id"), mock.call("bar_id")])
