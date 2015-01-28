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

from rally.common import plugin
from rally import exceptions
from tests.unit import test


@plugin.plugin("base_plugin")
class BasePlugin(plugin.Plugin):
    pass


@plugin.plugin("some_plugin")
class SomePlugin(BasePlugin):
    pass


@plugin.deprecated("some_reason", "0.1.1")
@plugin.plugin("deprecated_plugin")
class DeprecatedPlugin(BasePlugin):
    pass


class PluginModuleTestCase(test.TestCase):

    def test_deprecated(self):

        @plugin.deprecated("some", "0.0.1")
        def func():
            return 42

        self.assertEqual(func._plugin_deprecated,
                         {"reason": "some", "rally_version": "0.0.1"})

        self.assertEqual(func(), 42)

    def test_plugin(self):

        @plugin.plugin(name="test")
        def func():
            return 42

        self.assertEqual(func._plugin_name, "test")
        self.assertEqual(func(), 42)


class PluginTestCase(test.TestCase):

    def test_get_name(self):
        self.assertEqual("some_plugin", SomePlugin.get_name())

    def test_get(self):
        self.assertEqual(SomePlugin,
                         BasePlugin.get("some_plugin"))

    def test_get_not_found(self):
        self.assertRaises(exceptions.NoSuchPlugin,
                          BasePlugin.get, "non_existing")

    def test_get_all(self):
        self.assertEqual([SomePlugin, DeprecatedPlugin], BasePlugin.get_all())
        self.assertEqual([], SomePlugin.get_all())

    def test_is_deprecated(self):
        self.assertFalse(SomePlugin.is_deprecated())
        self.assertEqual(DeprecatedPlugin.is_deprecated(),
                         {"reason": "some_reason", "rally_version": "0.1.1"})
