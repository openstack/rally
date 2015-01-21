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
from tests.unit import fakes
from tests.unit import test


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

        @base.context(name="some_fake1", order=1)
        class SomeFake1(base.Context):
            pass

        @base.context(name="some_fake2", order=1)
        class SomeFake2(base.Context):
            pass

        mock_itersubclasses.return_value = [SomeFake1, SomeFake2]

        self.assertEqual(SomeFake1, base.Context.get_by_name("some_fake1"))
        self.assertEqual(SomeFake2, base.Context.get_by_name("some_fake2"))

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

    def test_lt(self):

        @base.context(name="fake_lt", order=fakes.FakeContext.get_order() - 1)
        class FakeLowerContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertTrue(FakeLowerContext(ctx) < fakes.FakeContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) < FakeLowerContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) < fakes.FakeContext(ctx))

    def test_gt(self):

        @base.context(name="fake_gt", order=fakes.FakeContext.get_order() + 1)
        class FakeBiggerContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertTrue(FakeBiggerContext(ctx) > fakes.FakeContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) > FakeBiggerContext(ctx))
        self.assertFalse(fakes.FakeContext(ctx) > fakes.FakeContext(ctx))

    def test_eq(self):

        @base.context(name="fake2", order=fakes.FakeContext.get_order() + 1)
        class FakeOtherContext(fakes.FakeContext):
            pass

        ctx = mock.MagicMock()
        self.assertFalse(FakeOtherContext(ctx) == fakes.FakeContext(ctx))
        self.assertTrue(FakeOtherContext(ctx) == FakeOtherContext(ctx))


class ContextManagerTestCase(test.TestCase):

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_validate(self, mock_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        base.ContextManager.validate(config)
        for ctx in ("ctx1", "ctx2"):
            mock_get.assert_has_calls([
                mock.call(ctx),
                mock.call().validate(config[ctx], non_hidden=False),
            ])

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_validate_non_hidden(self, mock_get):
        config = {
            "ctx1": mock.MagicMock(),
            "ctx2": mock.MagicMock()
        }

        base.ContextManager.validate(config, non_hidden=True)
        for ctx in ("ctx1", "ctx2"):
            mock_get.assert_has_calls([
                mock.call(ctx),
                mock.call().validate(config[ctx], non_hidden=True),
            ])

    def test_validate__non_existing_context(self):
        config = {
            "nonexisting": {"nonexisting": 2}
        }
        self.assertRaises(exceptions.NoSuchContext,
                          base.ContextManager.validate, config)

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_setup(self, mock_get_by_name):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_get_by_name.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}

        manager = base.ContextManager(ctx_object)
        result = manager.setup()

        self.assertEqual(result, ctx_object)
        mock_get_by_name.assert_has_calls([mock.call("a"), mock.call("b")],
                                          any_order=True)
        mock_context.assert_has_calls([mock.call(ctx_object),
                                       mock.call(ctx_object)], any_order=True)
        self.assertEqual([mock_context(), mock_context()], manager._visited)
        mock_context.return_value.assert_has_calls([mock.call.setup(),
                                                    mock.call.setup()],
                                                   any_order=True)

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_cleanup(self, mock_get_by_name):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_get_by_name.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}

        manager = base.ContextManager(ctx_object)
        manager.cleanup()
        mock_get_by_name.assert_has_calls([mock.call("a"), mock.call("b")],
                                          any_order=True)
        mock_context.assert_has_calls([mock.call(ctx_object),
                                       mock.call(ctx_object)], any_order=True)
        mock_context.return_value.assert_has_calls([mock.call.cleanup(),
                                                    mock.call.cleanup()],
                                                   any_order=True)

    @mock.patch("rally.benchmark.context.base.Context.get_by_name")
    def test_cleanup_exception(self, mock_get_by_name):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_context.cleanup.side_effect = Exception()
        mock_get_by_name.return_value = mock_context
        ctx_object = {"config": {"a": [], "b": []}}
        manager = base.ContextManager(ctx_object)
        manager.cleanup()

        mock_get_by_name.assert_has_calls([mock.call("a"), mock.call("b")],
                                          any_order=True)
        mock_context.assert_has_calls([mock.call(ctx_object),
                                       mock.call(ctx_object)], any_order=True)
        mock_context.return_value.assert_has_calls([mock.call.cleanup(),
                                                    mock.call.cleanup()],
                                                   any_order=True)

    @mock.patch("rally.benchmark.context.base.ContextManager.cleanup")
    @mock.patch("rally.benchmark.context.base.ContextManager.setup")
    def test_with_statement(self, mock_setup, mock_cleanup):
        with base.ContextManager(mock.MagicMock()):
            mock_setup.assert_called_once_with()
            mock_setup.reset_mock()
            self.assertFalse(mock_cleanup.called)
        self.assertFalse(mock_setup.called)
        mock_cleanup.assert_called_once_with()

    @mock.patch("rally.benchmark.context.base.ContextManager.cleanup")
    @mock.patch("rally.benchmark.context.base.ContextManager.setup")
    def test_with_statement_excpetion_during_setup(self, mock_setup,
                                                   mock_cleanup):
        mock_setup.side_effect = Exception("abcdef")

        try:
            with base.ContextManager(mock.MagicMock()):
                pass
        except Exception:
            pass
        finally:
            mock_setup.assert_called_once_with()
            mock_cleanup.assert_called_once_with()
