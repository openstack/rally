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

        class SubMeta(Meta):
            pass

        self.assertRaises(ReferenceError, Meta._meta_is_inited)
        self.assertFalse(Meta._meta_is_inited(raise_exc=False))

        self.assertRaises(ReferenceError, SubMeta._meta_is_inited)
        self.assertFalse(SubMeta._meta_is_inited(raise_exc=False))

        Meta._meta_init()

        self.assertTrue(Meta._meta_is_inited())
        self.assertTrue(Meta._meta_is_inited(raise_exc=False))

        self.assertRaises(ReferenceError, SubMeta._meta_is_inited)
        self.assertFalse(SubMeta._meta_is_inited(raise_exc=False))

        SubMeta._meta_init()

        self.assertTrue(SubMeta._meta_is_inited())
        self.assertTrue(SubMeta._meta_is_inited(raise_exc=False))

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
        self.assertEqual(42, Meta._meta_get("aaa"))

    def test_meta_get_default(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._meta_init()
        self.assertEqual(42, Meta._meta_get("b", 42))

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

    def test_default_meta_init(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._default_meta_init(False)
        self.assertIs(Meta, Meta._default_meta[0])
        self.assertEqual({}, Meta._default_meta[1])

    def test_default_meta_init_inherit(self):

        class MetaParent(meta.MetaMixin):
            pass

        MetaParent._default_meta_init(False)
        MetaParent._default_meta_set("a", 1)

        class MetaChildInherit(MetaParent):
            pass

        MetaChildInherit._default_meta_init(True)
        self.assertEqual(1, MetaChildInherit._default_meta_get("a", 5))

        class MetaChildNoInherit(MetaParent):
            pass

        MetaChildNoInherit._default_meta_init(False)
        self.assertEqual(5, MetaChildNoInherit._default_meta_get("a", 5))

    def test_default_meta_set_and_get(self):
        class Meta(meta.MetaMixin):
            pass

        Meta._default_meta_init(False)
        Meta._default_meta_set("b", 10)
        self.assertEqual(10, Meta._default_meta_get("b"))
        self.assertEqual(10, Meta._default_meta_get("b", 5))
        self.assertEqual(5, Meta._default_meta_get("c", 5))
        self.assertIsNone(Meta._default_meta_get("c"))

    def test_default_meta_set_from_children(self):

        class Meta(meta.MetaMixin):
            pass

        self.assertRaises(ReferenceError,
                          Meta._default_meta_set, "a", 1)
        self.assertRaises(ReferenceError,
                          Meta._default_meta_setdefault, "a", 1)

    def test_default_meta_set_default(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._default_meta_init(False)
        Meta._default_meta_setdefault("a", 1)
        Meta._default_meta_setdefault("a", 2)

        self.assertEqual(1, Meta._default_meta_get("a"))

    def test_meta_init_with_default_meta(self):

        class Meta(meta.MetaMixin):
            pass

        Meta._default_meta_init()
        Meta._default_meta_set("a", 10)
        Meta._default_meta_set("b", 20)

        class MetaChild(Meta):
            pass

        MetaChild._meta_init()
        self.assertEqual(10, MetaChild._meta_get("a"))
        self.assertEqual(20, MetaChild._meta_get("b"))
