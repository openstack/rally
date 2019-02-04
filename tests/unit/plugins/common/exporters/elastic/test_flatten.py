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

from rally.plugins.common.exporters.elastic import flatten
from tests.unit import test


class FlattenTestCase(test.TestCase):
    def test_transform(self):

        self.assertEqual(
            ["key1=value1", "key2=value2"],
            flatten.transform({"key1": "value1", "key2": "value2"}))

        self.assertEqual(
            ["key1=value1", "key2.foo.bar=1", "key2.xxx=yyy"],
            flatten.transform(
                {"key1": "value1", "key2": {"foo": {"bar": 1}, "xxx": "yyy"}}))

        self.assertEqual(
            ["foo[0]=xxx", "foo[1]=yyy", "foo[2].bar.zzz[0]=Hello",
             "foo[2].bar.zzz[1]=World!"],
            flatten.transform(
                {"foo": ["xxx", "yyy", {"bar": {"zzz": ["Hello", "World!"]}}]})
        )

    def test__join_keys(self):
        self.assertEqual("key", flatten._join_keys("key", ""))
        self.assertEqual("key.value", flatten._join_keys("key", "value"))
        self.assertEqual("[0].value", flatten._join_keys("[0]", "value"))
        self.assertEqual("key[0]", flatten._join_keys("key", "[0]"))
        self.assertEqual("[0][0]", flatten._join_keys("[0]", "[0]"))
