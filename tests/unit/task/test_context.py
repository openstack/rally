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

import collections
import ddt
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

    @ddt.data(({"test": 2}, True), ({"nonexisting": 2}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        results = context.Context.validate("fake", None, None, config)
        if valid:
            self.assertEqual([], results)
        else:
            self.assertEqual(1, len(results))

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

    def test_get_owner_id_from_task(self):
        ctx = {"config": {"fake": {"test": 10}}, "task": {"uuid": "task_uuid"}}
        ins = fakes.FakeContext(ctx)
        self.assertEqual("task_uuid", ins.get_owner_id())

    def test_get_owner_id(self):
        ctx = {"config": {"fake": {"test": 10}}, "task": {"uuid": "task_uuid"},
               "owner_id": "foo_uuid"}
        ins = fakes.FakeContext(ctx)
        self.assertEqual("foo_uuid", ins.get_owner_id())


class ContextManagerTestCase(test.TestCase):
    @mock.patch("rally.task.context.ContextManager._get_sorted_context_lst")
    def test_setup(self, mock__get_sorted_context_lst):
        foo_context = mock.MagicMock()
        bar_context = mock.MagicMock()
        mock__get_sorted_context_lst.return_value = [foo_context, bar_context]

        ctx_object = {"config": {"a": [], "b": []},
                      "scenario_namespace": "foo"}

        manager = context.ContextManager(ctx_object)
        result = manager.setup()

        self.assertEqual(result, ctx_object)
        foo_context.setup.assert_called_once_with()
        bar_context.setup.assert_called_once_with()

    @mock.patch("rally.task.context.Context.get_all")
    @mock.patch("rally.task.context.Context.get")
    def test_get_sorted_context_lst(self, mock_context_get,
                                    mock_context_get_all):

        # use ordereddict to predict the order of calls
        ctx_object = {"config": collections.OrderedDict([("a@foo", []),
                                                         ("b", []),
                                                         ("c", []),
                                                         ("d", [])]),
                      "scenario_namespace": "foo"}

        def OrderableMock(**kwargs):
            return mock.Mock(__lt__=(lambda x, y: x), **kwargs)

        a_ctx = mock.Mock(return_value=OrderableMock())
        mock_context_get.return_value = a_ctx

        b_ctx = mock.Mock(return_value=OrderableMock())
        c_ctx = mock.Mock(get_namespace=lambda: "foo",
                          return_value=OrderableMock())
        d_ctx = mock.Mock(get_namespace=lambda: "default",
                          return_value=OrderableMock())
        all_plugins = {
            # it is a case when search is performed for any namespace and only
            # one possible match is found
            "b": [b_ctx],
            # it is a case when plugin should be filtered by the scenario
            # namespace
            "c": [mock.Mock(get_namespace=lambda: "default"), c_ctx],
            # it is a case when plugin should be filtered by the scenario
            # namespace
            "d": [mock.Mock(get_namespace=lambda: "bar"), d_ctx]
        }

        def fake_get_all(name, allow_hidden=True):
            # use pop to ensure that get_all is called only one time per ctx
            result = all_plugins.pop(name, None)
            if result is None:
                self.fail("Unexpected call of Context.get_all for %s plugin" %
                          name)
            return result

        mock_context_get_all.side_effect = fake_get_all

        manager = context.ContextManager(ctx_object)

        self.assertEqual({a_ctx.return_value, b_ctx.return_value,
                          c_ctx.return_value, d_ctx.return_value},
                         set(manager._get_sorted_context_lst()))

        mock_context_get.assert_called_once_with("a", namespace="foo",
                                                 fallback_to_default=False,
                                                 allow_hidden=True)
        a_ctx.assert_called_once_with(ctx_object)
        self.assertEqual([mock.call(name=name, allow_hidden=True)
                          for name in ("b", "c", "d")],
                         mock_context_get_all.call_args_list)

    @mock.patch("rally.task.context.Context.get_all")
    def test_get_sorted_context_lst_fails(self, mock_context_get_all):
        ctx_object = {"config": {"foo": "bar"},
                      "scenario_namespace": "foo"}

        mock_context_get_all.return_value = []
        manager = context.ContextManager(ctx_object)

        self.assertRaises(exceptions.PluginNotFound,
                          manager._get_sorted_context_lst)

        mock_context_get_all.assert_called_once_with(name="foo",
                                                     allow_hidden=True)

    @mock.patch("rally.task.context.Context.get")
    def test_cleanup(self, mock_context_get):
        mock_context = mock.MagicMock()
        mock_context.return_value = mock.MagicMock(__lt__=lambda x, y: True)
        mock_context_get.return_value = mock_context
        ctx_object = {"config": {"a@foo": [], "b@foo": []}}

        manager = context.ContextManager(ctx_object)
        manager.cleanup()
        mock_context_get.assert_has_calls(
            [mock.call("a", namespace="foo", allow_hidden=True,
                       fallback_to_default=False),
             mock.call("b", namespace="foo", allow_hidden=True,
                       fallback_to_default=False)],
            any_order=True)
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
        ctx_object = {"config": {"a@foo": [], "b@foo": []}}
        manager = context.ContextManager(ctx_object)
        manager.cleanup()

        mock_context_get.assert_has_calls(
            [mock.call("a", namespace="foo", allow_hidden=True,
                       fallback_to_default=False),
             mock.call("b", namespace="foo", allow_hidden=True,
                       fallback_to_default=False)],
            any_order=True)
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
    def test_with_statement_exception_during_setup(
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
