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

from rally.common.plugin import meta
from tests.unit import test


class TestMetaMixinTestCase(test.TestCase):

    def test_meta_is_inited(self):

        class Meta(meta.MetaMixin):
            pass

        self.assertRaises(ReferenceError, Meta._meta_is_inited)
        self.assertFalse(Meta._meta_is_inited(raise_exc=False))

        Meta._meta_init()

        self.assertTrue(Meta._meta_is_inited())
        self.assertTrue(Meta._meta_is_inited(raise_exc=False))

    def test_meta_clear(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._meta_init()
        Meta._meta_set("aaa", 42)

        meta_ref = Meta._meta
        Meta._meta_clear()
        self.assertRaises(AttributeError, getattr, Meta, "_meta")
        self.assertEqual({}, meta_ref)

    def test_meta_set_and_get(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._meta_init()
        Meta._meta_set("aaa", 42)
        self.assertEqual(Meta._meta_get("aaa"), 42)

    def test_meta_get_default(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._meta_init()
        self.assertEqual(Meta._meta_get("b", 42), 42)

    def test_meta_get_if_is_not_inited(self):

        class Meta(meta.MetaMixin):
            pass

        self.assertRaises(ReferenceError, Meta._meta_get, "any")

    def test_meta_set_if_is_not_inited(self):

        class Meta(meta.MetaMixin):
            pass

        self.assertRaises(ReferenceError, Meta._meta_set, "a", 1)

    def test_meta_setdefault(self):

        class Meta(meta.MetaMixin):
            pass

        self.assertRaises(ReferenceError, Meta._meta_setdefault, "any", 42)
        Meta._meta_init()

        Meta._meta_setdefault("any", 42)
        self.assertEqual(42, Meta._meta_get("any"))
        Meta._meta_setdefault("any", 2)
        self.assertEqual(42, Meta._meta_get("any"))
