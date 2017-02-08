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

from yaml import constructor

from rally.common import yamlutils
from tests.unit import test


class YamlTestcase(test.TestCase):
    """Test yaml loading method."""

    def setUp(self):
        super(YamlTestcase, self).setUp()

    def test_safe_load(self):
        stream = "{'a': 1, 'b': {'a': 2}}"
        stream_obj = yamlutils.safe_load(stream)
        self.assertEqual({"a": 1, "b": {"a": 2}},
                         stream_obj)

    def test_safe_load_duplicate_key(self):
        stream = "{'a': 1, 'a': 2}"
        self.assertRaises(constructor.ConstructorError,
                          yamlutils.safe_load, stream)

    def test_safe_load_order_key(self):
        stream = "{'b': 1, 'a': 1, 'c': 1}"
        stream_obj = yamlutils.safe_load(stream)
        self.assertEqual({"a": 1, "b": 1, "c": 1}, stream_obj)
        self.assertEqual(["b", "a", "c"], list(stream_obj))
