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

import jsonschema

from rally.env import env_mgr
from rally.env import platform

from tests.unit import test


class PlatformBaseTestCase(test.TestCase):

    def _check_schema(self, schema, obj):
        jsonschema.validate(obj, schema)

    def _check_health_schema(self, obj):
        self._check_schema(env_mgr.EnvManager._HEALTH_FORMAT, obj)

    def _check_cleanup_schema(self, obj):
        self._check_schema(env_mgr.EnvManager._CLEANUP_FORMAT, obj)

    def _check_info_schema(self, obj):
        self._check_schema(env_mgr.EnvManager._INFO_FORMAT, obj)


class PlatformTestCase(test.TestCase):

    def test_plugin_configure_and_methods(self):

        @platform.configure(name="existing", platform="foo")
        class FooPlugin(platform.Platform):
            pass

        self.addCleanup(FooPlugin.unregister)

        f = FooPlugin("spec", "uuid", "plugin_data", "platform_data", "status")
        self.assertEqual(f.uuid, "uuid")
        self.assertEqual(f.spec, "spec")
        self.assertEqual(f.plugin_data, "plugin_data")
        self.assertEqual(f.platform_data, "platform_data")
        self.assertEqual(f.status, "status")

        self.assertRaises(NotImplementedError, f.create)
        self.assertRaises(NotImplementedError, f.destroy)
        self.assertRaises(NotImplementedError, f.update, "new_spec")
        self.assertRaises(NotImplementedError, f.cleanup)
        self.assertRaises(NotImplementedError,
                          f.cleanup, task_uuid="task_uuid")
        self.assertRaises(NotImplementedError, f.check_health)
        self.assertRaises(NotImplementedError, f.info)
