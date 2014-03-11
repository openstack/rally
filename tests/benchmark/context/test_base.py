# Copyright 2014: Mirantis Inc.
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
import mock

from rally.benchmark.context import base
from rally import exceptions
from tests import fakes
from tests import test


class BaseContextTestCase(test.TestCase):

    def test_init(self):
        context = {
            "config": {
                "a": 1,
                "fake": mock.MagicMock()
            },
            "task": mock.MagicMock()
        }

        ctx = fakes.FakeContext(context)
        self.assertEqual(ctx.config, context["config"]["fake"])
        self.assertEqual(ctx.task, context["task"])
        self.assertEqual(ctx.context, context)

    def test_init_empty_context(self):
        context = {
            "task": mock.MagicMock()
        }
        ctx = fakes.FakeContext(context)
        self.assertEqual(ctx.config, {})
        self.assertEqual(ctx.task, context["task"])
        self.assertEqual(ctx.context, context)

    def test_validate__context(self):
        context = {
            "fake": {"test": 2}
        }
        base.Context.validate(context)

    def test_validate__wrong_context(self):
        context = {
            "fake": {"nonexisting": 2}
        }
        self.assertRaises(jsonschema.ValidationError,
                          base.Context.validate, context)

    def test_validate__non_existing_context(self):
        config = {
            "nonexisting": {"nonexisting": 2}
        }
        self.assertRaises(exceptions.NoSuchContext,
                          base.Context.validate, config)

    @mock.patch("rally.benchmark.context.base.utils.itersubclasses")
    def test_get_by_name(self, mock_itersubclasses):
        A = mock.MagicMock()
        A.__ctx_name__ = "a"
        B = mock.MagicMock()
        B.__ctx_name__ = "b"
        mock_itersubclasses.return_value = [A, B]

        self.assertEqual(A, base.Context.get_by_name("a"))
        self.assertEqual(B, base.Context.get_by_name("b"))

    @mock.patch("rally.benchmark.context.base.utils.itersubclasses")
    def test_get_by_name_non_existing(self, mock_itersubclasses):
        mock_itersubclasses.return_value = []
        self.assertRaises(exceptions.NoSuchContext,
                          base.Context.get_by_name, "nonexisting")

    def test_setup_is_abstract(self):

        class A(base.Context):

            def cleanup(self):
                pass

        self.assertRaises(TypeError, A)

    def test_cleanup_is_abstract(self):
        class A(base.Context):

            def setup(self):
                pass

        self.assertRaises(TypeError, A)

    def test_with_statement(self):
        context = {
            "task": mock.MagicMock()
        }
        ctx = fakes.FakeContext(context)
        ctx.setup = mock.MagicMock()
        ctx.cleanup = mock.MagicMock()

        with ctx as entered_ctx:
            self.assertEqual(ctx, entered_ctx)

        ctx.cleanup.assert_called_once_with()
