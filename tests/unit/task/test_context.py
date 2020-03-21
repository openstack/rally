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

from unittest import mock

import ddt

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
        self.assertEqual(expected, ins.config)
        self.assertEqual("foo_task", ins.task)
        self.assertEqual(ctx, ins.context)

    def test_init_with_default_config(self):
        @context.configure(name="foo", order=1)
        class FooContext(fakes.FakeContext):
            DEFAULT_CONFIG = {"alpha": "beta", "delta": "gamma"}

        self.addCleanup(FooContext.unregister)

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
        self.assertEqual(ctx0["config"]["fake"], ctx.config)
        self.assertEqual(ctx0["task"], ctx.task)
        self.assertEqual(ctx0, ctx.context)

    @ddt.data(({"test": 2}, True), ({"nonexisting": 2}, False))
    @ddt.unpack
    def test_validate(self, config, valid):
        results = context.Context.validate("fake", None, None, config)
        if valid:
            self.assertEqual(results, [])
        else:
            self.assertEqual(1, len(results))

    def test_setup_is_abstract(self):

        @context.configure("test_abstract_setup", 0)
        class A(context.Context):

            def cleanup(self):
                pass

        self.addCleanup(A.unregister)
        self.assertRaises(TypeError, A)

    def test_cleanup_is_abstract(self):

        @context.configure("test_abstract_cleanup", 0)
        class A(context.Context):

            def setup(self):
                pass

        self.addCleanup(A.unregister)
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

    def test_get_owner_id_from_task(self):
        ctx = {"config": {"fake": {"test": 10}}, "task": {"uuid": "task_uuid"}}
        ins = fakes.FakeContext(ctx)
        self.assertEqual("task_uuid", ins.get_owner_id())

    def test_get_owner_id(self):
        ctx = {"config": {"fake": {"test": 10}}, "task": {"uuid": "task_uuid"},
               "owner_id": "foo_uuid"}
        ins = fakes.FakeContext(ctx)
        self.assertEqual("foo_uuid", ins.get_owner_id())

    def test___eq__(self):
        @context.configure(name="bar", order=1)
        class BarContext(fakes.FakeContext):
            pass

        foo_context = fakes.FakeContext()
        bar_context = BarContext()
        self.assertTrue(foo_context == bar_context)

    def test___lt__(self):
        @context.configure(name="barlt", order=2)
        class BarContext(fakes.FakeContext):
            pass

        foo_context = fakes.FakeContext()
        bar_context = BarContext()
        self.assertTrue(foo_context < bar_context)

    def test___gt__(self):
        @context.configure(name="bargt", order=0)
        class BarContext(fakes.FakeContext):
            pass

        foo_context = fakes.FakeContext()
        bar_context = BarContext()
        self.assertTrue(foo_context > bar_context)

    def test___le__(self):
        @context.configure(name="barle", order=1)
        class BarContext(fakes.FakeContext):
            pass

        @context.configure(name="bazle", order=2)
        class BazContext(fakes.FakeContext):
            pass

        foo_context = fakes.FakeContext()
        bar_context = BarContext()
        baz_context = BazContext()
        self.assertTrue(foo_context <= bar_context)
        self.assertTrue(foo_context <= baz_context)

    def test___ge__(self):
        @context.configure(name="barge", order=0)
        class BarContext(fakes.FakeContext):
            pass

        @context.configure(name="bazge", order=-1)
        class BazContext(fakes.FakeContext):
            pass

        foo_context = fakes.FakeContext()
        bar_context = BarContext()
        baz_context = BazContext()
        self.assertTrue(foo_context >= bar_context)
        self.assertTrue(foo_context >= baz_context)


class ContextManagerTestCase(test.TestCase):
    @mock.patch("rally.task.context.ContextManager._get_sorted_context_lst")
    def test_setup(self, mock__get_sorted_context_lst):
        foo_context = mock.MagicMock()
        bar_context = mock.MagicMock()
        mock__get_sorted_context_lst.return_value = [foo_context, bar_context]

        ctx_object = {"config": {"a": [], "b": []}, "task": {"uuid": "uuid"}}

        manager = context.ContextManager(ctx_object)
        result = manager.setup()

        self.assertEqual(result, ctx_object)
        foo_context.setup.assert_called_once_with()
        bar_context.setup.assert_called_once_with()

        self.assertEqual([
            {
                "plugin_cfg": foo_context.config,
                "plugin_name": foo_context.get_fullname.return_value,
                "setup": {
                    "atomic_actions": foo_context.atomic_actions.return_value,
                    "error": None,
                    "started_at": mock.ANY,
                    "finished_at": mock.ANY
                },
                "cleanup": {
                    "atomic_actions": None,
                    "error": None,
                    "started_at": None,
                    "finished_at": None}
            },
            {
                "plugin_cfg": bar_context.config,
                "plugin_name": bar_context.get_fullname.return_value,
                "setup": {
                    "atomic_actions": bar_context.atomic_actions.return_value,
                    "error": None,
                    "started_at": mock.ANY,
                    "finished_at": mock.ANY
                },
                "cleanup": {
                    "atomic_actions": None,
                    "error": None,
                    "started_at": None,
                    "finished_at": None}
            }], manager.contexts_results())

    @mock.patch("rally.task.context.task_utils.format_exc")
    @mock.patch("rally.task.context.ContextManager._get_sorted_context_lst")
    def test_setup_fails(self, mock__get_sorted_context_lst, mock_format_exc):
        special_exc = KeyError("Oops")
        foo_context = mock.MagicMock()
        foo_context.setup.side_effect = special_exc
        bar_context = mock.MagicMock()
        mock__get_sorted_context_lst.return_value = [foo_context, bar_context]

        ctx_object = {"config": {"a": [], "b": []}, "task": {"uuid": "uuid"}}

        manager = context.ContextManager(ctx_object)

        e = self.assertRaises(KeyError, manager.setup)
        self.assertEqual(special_exc, e)

        foo_context.setup.assert_called_once_with()
        self.assertFalse(bar_context.setup.called)

        self.assertEqual([
            {
                "plugin_cfg": foo_context.config,
                "plugin_name": foo_context.get_fullname.return_value,
                "setup": {
                    "atomic_actions": foo_context.atomic_actions.return_value,
                    "error": mock_format_exc.return_value,
                    "started_at": mock.ANY,
                    "finished_at": mock.ANY
                },
                "cleanup": {
                    "atomic_actions": None,
                    "error": None,
                    "started_at": None,
                    "finished_at": None}
            }], manager.contexts_results())
        mock_format_exc.assert_called_once_with(special_exc)

    def test_get_sorted_context_lst(self):

        @context.configure("foo", order=1)
        class A(context.Context):

            def setup(self):
                pass

            def cleanup(self):
                pass

        @context.configure("foo", platform="foo", order=0)
        class B(A):
            pass

        @context.configure("boo", platform="foo", order=2)
        class C(A):
            pass

        self.addCleanup(A.unregister)
        self.addCleanup(B.unregister)
        self.addCleanup(C.unregister)

        ctx_obj = {"config": {"foo@default": [], "boo": [], "foo@foo": []}}
        ctx_insts = context.ContextManager(ctx_obj)._get_sorted_context_lst()
        self.assertEqual(3, len(ctx_insts))
        self.assertIsInstance(ctx_insts[0], B)
        self.assertIsInstance(ctx_insts[1], A)
        self.assertIsInstance(ctx_insts[2], C)

    @mock.patch("rally.task.context.Context.get_all")
    def test_get_sorted_context_lst_fails(self, mock_context_get_all):

        ctx_object = {"config": {"foo": "bar"}}

        mock_context_get_all.return_value = []
        manager = context.ContextManager(ctx_object)

        self.assertRaises(exceptions.PluginNotFound,
                          manager._get_sorted_context_lst)

        mock_context_get_all.assert_called_once_with(
            name="foo", platform=None, allow_hidden=True)

    def test_cleanup(self):
        mock_obj = mock.MagicMock()

        @context.configure("a", platform="foo", order=1)
        class A(context.Context):

            def setup(self):
                pass

            def cleanup(self):
                mock_obj("a@foo")

        self.addCleanup(A.unregister)

        @context.configure("b", platform="foo", order=2)
        class B(context.Context):

            def setup(self):
                pass

            def cleanup(self):
                mock_obj("b@foo")

        ctx_object = {
            "config": {"a@foo": [], "b@foo": []},
            "task": {"uuid": "uuid"}
        }
        context.ContextManager(ctx_object).cleanup()
        mock_obj.assert_has_calls([mock.call("b@foo"), mock.call("a@foo")])

    @mock.patch("rally.task.context.task_utils.format_exc")
    @mock.patch("rally.task.context.LOG.exception")
    def test_cleanup_exception(self, mock_log_exception, mock_format_exc):
        mock_obj = mock.MagicMock()

        exc = Exception("So Sad")

        @context.configure("a", platform="foo", order=1)
        class A(context.Context):

            def setup(self):
                pass

            def cleanup(self):
                mock_obj("a@foo")
                raise exc

        self.addCleanup(A.unregister)
        ctx_object = {"config": {"a@foo": []}, "task": {"uuid": "uuid"}}

        ctx_manager = context.ContextManager(ctx_object)
        ctx_manager._data[A.get_fullname()] = {
            "cleanup": {"atomic_actions": None,
                        "started_at": None,
                        "finished_at": None,
                        "error": None}}

        ctx_manager.cleanup()

        mock_obj.assert_called_once_with("a@foo")
        mock_log_exception.assert_called_once_with(mock.ANY)
        mock_format_exc.assert_called_once_with(exc)
        self.assertEqual([{
            "cleanup": {
                "atomic_actions": [],
                "error": mock_format_exc.return_value,
                "started_at": mock.ANY,
                "finished_at": mock.ANY}}],
            ctx_manager.contexts_results())

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
