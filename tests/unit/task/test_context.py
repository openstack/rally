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

import ddt
import jsonschema
import mock

from rally import exceptions
from rally.task import context
from tests.unit import fakes
from tests.unit import test


@ddt.ddt
class BaseContextTestCase(test.TestCase):

    @ddt.data({"config": {"bar": "spam"}, "expected": {"bar": "spam"}},
              {"config": {"bar": "spam"}, "expected": {"bar": "spam"}},
              {"config": {}, "expected": {}},
              {"config": None, "expected": None},
              {"config": 42, "expected": 42},
              {"config": "foo str", "expected": "foo str"},
              {"config": [], "expected": ()},
              {"config": [11, 22, 33], "expected": (11, 22, 33)})
    @ddt.unpack
    def test_init(self, config, expected):
        ctx = {"config": {"foo": 42, "fake": config}, "task": "foo_task"}
        ins = fakes.FakeContext(ctx)
        self.assertEqual(ins.config, expected)
        self.assertEqual(ins.task, "foo_task")
        self.assertEqual(ins.context, ctx)

    def test_init_with_default_config(self):
        @context.configure(name="foo", order=1)
        class FooContext(fakes.FakeContext):
            DEFAULT_CONFIG = {"alpha": "beta", "delta": "gamma"}

        ctx = {"config": {"foo": {"ab": "cd"}, "bar": 42}, "task": "foo_task"}
        ins = FooContext(ctx)
        self.assertEqual({"ab": "cd", "alpha": "beta", "delta": "gamma"},
                         ins.config)

    def test_init_empty_context(self):
        ctx0 = {
            "task": mock.MagicMock(),
            "config": {"fake": {"foo": 42}}
        }
        ctx = fakes.FakeContext(ctx0)
        self.assertEqual(ctx.config, ctx0["config"]["fake"])
        self.assertEqual(ctx.task, ctx0["task"])
        self.assertEqual(ctx.context, ctx0)

    def test_validate__context(self):
        fakes.FakeContext.validate({"test": 2})

    def test_validate__wrong_context(self):
        self.assertRaises(jsonschema.ValidationError,
                          fakes.FakeContext.validate, {"nonexisting": 2})

    def test_validate__hidden(self):
        fakes.FakeHiddenContext.validate({"test": 2})
        self.assertRaises(exceptions.PluginNotFound,
                          fakes.FakeHiddenContext.validate,
                          {"test": 2}, non_hidden=True)

    def test_setup_is_abstract(self):

        @context.configure("test_abstract_setup", 0)
        class A(context.Context):

            def cleanup(self):
                pass

        self.assertRaises(TypeError, A)

    def test_cleanup_is_abstract(self):

        @context.configure("test_abstract_cleanup", 0)
        class A(context.Context):

            def setup(self):
                pass

        self.assertRaises(TypeError, A)

    def test_with_statement(self):
        ctx0 = {
            "task": mock.MagicMock()
        }
        ctx = fakes.FakeContext(ctx0)
        ctx.setup = mock.MagicMock()
        ctx.cleanup = mock.MagicMock()

        with ctx as entered_ctx:
            self.assertEqual(ctx, entered_ctx)

        ctx.cleanup.assert_called_once_with()

    def test_lt(self):

        @context.configure(name="lt", order=fakes.FakeContext.get_order() - 1)
        class FakeLowerContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertTrue(FakeLowerContext(ctx) < fakes.FakeContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) < FakeLowerContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) < fakes.FakeContext(ctx))

    def test_gt(self):

        @context.configure(name="f", order=fakes.FakeContext.get_order() + 1)
        class FakeBiggerContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertTrue(FakeBiggerContext(ctx) > fakes.FakeContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) > FakeBiggerContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) > fakes.FakeContext(ctx))

    def test_eq(self):

        @context.configure(name="fake2",
                           order=fakes.FakeContext.get_order() + 1)
        class FakeOtherContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertFalse(FakeOtherContext(ctx) == fakes.FakeContext(ctx))
        self.assertTrue(FakeOtherContext(ctx) == FakeOtherContext(ctx))


class ContextManagerTestCase(test.TestCase):

    @mock.patch("rally.task.context.Context.get")
    def test_validate(self, mock_context_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        context.ContextManager.validate(config)
        for ctx in ("ctx1", "ctx2"):
            mock_context_get.assert_has_calls([
                mock.call(ctx),
                mock.call().validate(config[ctx], non_hidden=False),
            ])

    @mock.patch("rally.task.context.Context.get")
    def test_validate_non_hidden(self, mock_context_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        context.ContextManager.validate(config, non_hidden=True)
        for ctx in ("ctx1", "ctx2"):
            mock_context_get.assert_has_calls([
                mock.call(ctx),
                mock.call().validate(config[ctx], non_hidden=True),
            ])

    def test_validate__non_existing_context(self):
        config = {
            "nonexisting": {"nonexisting": 2}
        }
        self.assertRaises(exceptions.PluginNotFound,
                          context.ContextManager.validate, config)

    @mock.patch("rally.task.context.Context.get")
    def test_setup(self, mock_context_get):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_context_get.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}

        manager = context.ContextManager(ctx_object)
        result = manager.setup()

        self.assertEqual(result, ctx_object)
        mock_context_get.assert_has_calls(
            [mock.call("a"), mock.call("b")], any_order=True)
        mock_context.assert_has_calls(
            [mock.call(ctx_object), mock.call(ctx_object)], any_order=True)
        self.assertEqual([mock_context(), mock_context()], manager._visited)
        mock_context.return_value.assert_has_calls(
            [mock.call.setup(), mock.call.setup()], any_order=True)

    @mock.patch("rally.task.context.Context.get")
    def test_cleanup(self, mock_context_get):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_context_get.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}

        manager = context.ContextManager(ctx_object)
        manager.cleanup()
        mock_context_get.assert_has_calls(
            [mock.call("a"), mock.call("b")], any_order=True)
        mock_context.assert_has_calls(
            [mock.call(ctx_object), mock.call(ctx_object)], any_order=True)
        mock_context.return_value.assert_has_calls(
            [mock.call.cleanup(), mock.call.cleanup()], any_order=True)

    @mock.patch("rally.task.context.Context.get")
    def test_cleanup_exception(self, mock_context_get):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_context.cleanup.side_effect = Exception()
        mock_context_get.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}
        manager = context.ContextManager(ctx_object)
        manager.cleanup()

        mock_context_get.assert_has_calls(
            [mock.call("a"), mock.call("b")], any_order=True)
        mock_context.assert_has_calls(
            [mock.call(ctx_object), mock.call(ctx_object)], any_order=True)
        mock_context.return_value.assert_has_calls(
            [mock.call.cleanup(), mock.call.cleanup()], any_order=True)

    @mock.patch("rally.task.context.ContextManager.cleanup")
    @mock.patch("rally.task.context.ContextManager.setup")
    def test_with_statement(
            self, mock_context_manager_setup, mock_context_manager_cleanup):
        with context.ContextManager(mock.MagicMock()):
            mock_context_manager_setup.assert_called_once_with()
            mock_context_manager_setup.reset_mock()
            self.assertFalse(mock_context_manager_cleanup.called)
        self.assertFalse(mock_context_manager_setup.called)
        mock_context_manager_cleanup.assert_called_once_with()

    @mock.patch("rally.task.context.ContextManager.cleanup")
    @mock.patch("rally.task.context.ContextManager.setup")
    def test_with_statement_excpetion_during_setup(
            self, mock_context_manager_setup, mock_context_manager_cleanup):
        mock_context_manager_setup.side_effect = Exception("abcdef")

        try:
            with context.ContextManager(mock.MagicMock()):
                pass
        except Exception:
            pass
        finally:
            mock_context_manager_setup.assert_called_once_with()
            mock_context_manager_cleanup.assert_called_once_with()
