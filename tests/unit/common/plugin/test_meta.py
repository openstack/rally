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

    def test_default_meta(self):

        class Meta(meta.MetaMixin):
            DEFAULT_META = {"foo": "bar"}

        class SubMeta(Meta):
            pass

        class SubMetaWithDefault(Meta):
            DEFAULT_META = {"foo": "spam"}

        class SubSubMeta(SubMeta):
            DEFAULT_META = {"baz": "eggs"}

        Meta._meta_init()
        SubMeta._meta_init()
        SubMetaWithDefault._meta_init()
        SubSubMeta._meta_init()

        self.assertEqual("bar", Meta._meta_get("foo"))
        self.assertEqual("bar", SubMeta._meta_get("foo"))
        self.assertEqual("spam", SubMetaWithDefault._meta_get("foo"))
        self.assertEqual("bar", SubSubMeta._meta_get("foo"))
        self.assertEqual("eggs", SubSubMeta._meta_get("baz"))
        self.assertIsNone(Meta._meta_get("baz"))
        self.assertIsNone(SubMeta._meta_get("baz"))
        self.assertIsNone(SubMetaWithDefault._meta_get("baz"))

    def test_default_meta_change(self):

        class Meta(meta.MetaMixin):
            DEFAULT_META = {"foo": []}

        class SubMeta(Meta):
            pass

        Meta._meta_init()
        SubMeta._meta_init()

        self.assertEqual([], Meta._meta_get("foo"))
        self.assertEqual([], SubMeta._meta_get("foo"))

        SubMeta._meta_get("foo").append("bar")

        self.assertEqual([], Meta._meta_get("foo"))
        self.assertEqual(["bar"], SubMeta._meta_get("foo"))

        Meta._meta_get("foo").append("baz")

        self.assertEqual(["baz"], Meta._meta_get("foo"))
        self.assertEqual(["bar"], SubMeta._meta_get("foo"))

    def test_default_meta_validators(self):

        class A(meta.MetaMixin):
            DEFAULT_META = {"validators": ["a"]}

        class B(A):
            DEFAULT_META = {"validators": ["b", "foo"]}

        class C(A):
            DEFAULT_META = {"validators": ["c", "foo"]}

        class D(B, C):
            DEFAULT_META = {"validators": ["d"]}

        A._meta_init()
        B._meta_init()
        C._meta_init()
        D._meta_init()

        self.assertEqual(["a"], A._meta_get("validators"))
        self.assertEqual(["a", "b", "foo"], B._meta_get("validators"))
        self.assertEqual(["a", "c", "foo"], C._meta_get("validators"))
        self.assertEqual(["a", "c", "foo", "b", "foo", "d"],
                         D._meta_get("validators"))

    def test_default_meta_context(self):

        class A(meta.MetaMixin):
            DEFAULT_META = {"context": {"foo": "a"}}

        class B(A):
            DEFAULT_META = {"context": {"foo": "b", "baz": "b"}}

        class C(A):
            DEFAULT_META = {"context": {"foo": "c", "spam": "c"}}

        class D(B, C):
            DEFAULT_META = {"context": {"bar": "d"}}

        A._meta_init()
        B._meta_init()
        C._meta_init()
        D._meta_init()

        self.assertEqual({"foo": "a"}, A._meta_get("context"))
        self.assertEqual({"foo": "b", "baz": "b"}, B._meta_get("context"))
        self.assertEqual({"foo": "c", "spam": "c"}, C._meta_get("context"))
        self.assertEqual({"foo": "b", "baz": "b", "spam": "c", "bar": "d"},
                         D._meta_get("context"))
