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
        fakes.FakeContext.validate({"test": 2})

    def test_validate__wrong_context(self):
        self.assertRaises(jsonschema.ValidationError,
                          fakes.FakeContext.validate, {"nonexisting": 2})

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

    def test_get_by_name_hidder(self):
        self.assertRaises(exceptions.NoSuchContext,
                          base.Context.validate, {}, non_hidden=True)

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


class ContextManagerTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.base.ContextManager._magic")
    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_run(self, mock_get, mock_magic):
        context = {
            "config": {
                "a": mock.MagicMock(),
                "b": mock.MagicMock()
            }
        }

        cc = mock.MagicMock()
        cc.__ctx_order__ = 10
        mock_get.return_value = cc

        mock_magic.return_value = 5

        result = base.ContextManager.run(context, lambda x, y: x + y, 1, 2)
        self.assertEqual(result, 5)

        mock_get.assert_has_calls([
            mock.call("a"),
            mock.call("b"),
            mock.call()(context),
            mock.call()(context)
        ])

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_validate(self, mock_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        base.ContextManager.validate(config)
        mock_get.assert_has_calls([
            mock.call("ctx1"),
            mock.call().validate(config["ctx1"], non_hidden=False),
            mock.call("ctx2"),
            mock.call().validate(config["ctx2"], non_hidden=False)
        ])

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_validate_semantic(self, mock_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        base.ContextManager.validate_semantic(config)
        mock_get.assert_has_calls([
            mock.call("ctx1"),
            mock.call().validate_semantic(config["ctx1"], admin=None,
                                          users=None, task=None),
            mock.call("ctx2"),
            mock.call().validate_semantic(config["ctx2"], admin=None,
                                          users=None, task=None)
        ])

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_validate_non_hidden(self, mock_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        base.ContextManager.validate(config, non_hidden=True)
        mock_get.assert_has_calls([
            mock.call("ctx1"),
            mock.call().validate(config["ctx1"], non_hidden=True),
            mock.call("ctx2"),
            mock.call().validate(config["ctx2"], non_hidden=True)
        ])

    def test_validate__non_existing_context(self):
        config = {
            "nonexisting": {"nonexisting": 2}
        }
        self.assertRaises(exceptions.NoSuchContext,
                          base.ContextManager.validate, config)

    def test__magic(self):
        func = lambda x, y: x + y

        result = base.ContextManager._magic([], func, 2, 3)
        self.assertEqual(result, 5)

    def test__magic_with_ctx(self):
        ctx = [mock.MagicMock(), mock.MagicMock()]
        func = lambda x, y: x + y

        result = base.ContextManager._magic(ctx, func, 2, 3)
        self.assertEqual(result, 5)

        expected = [mock.call.__enter__(), mock.call.setup(),
                    mock.call.__exit__(None, None, None)]
        for c in ctx:
            ctx[0].assert_has_calls(expected)
