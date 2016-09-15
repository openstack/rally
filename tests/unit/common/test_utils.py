# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import print_function
import collections
import string
import sys
import threading
import time

import ddt
import mock
from six.moves import queue as Queue
import testtools

from rally.common import utils
from rally import exceptions
from tests.unit import test


class ImmutableMixinTestCase(test.TestCase):

    def test_without_base_values(self):
        im = utils.ImmutableMixin()
        self.assertRaises(exceptions.ImmutableException,
                          im.__setattr__, "test", "test")

    def test_with_base_values(self):

        class A(utils.ImmutableMixin):
            def __init__(self, test):
                self.test = test
                super(A, self).__init__()

        a = A("test")
        self.assertRaises(exceptions.ImmutableException,
                          a.__setattr__, "abc", "test")
        self.assertEqual(a.test, "test")


class EnumMixinTestCase(test.TestCase):

    def test_enum_mix_in(self):

        class Foo(utils.EnumMixin):
            a = 10
            b = 20
            CC = "2000"

        self.assertEqual(set(list(Foo())), set([10, 20, "2000"]))

    def test_with_underscore(self):

        class Foo(utils.EnumMixin):
            a = 10
            b = 20
            _CC = "2000"

        self.assertEqual(set(list(Foo())), set([10, 20]))


class StdIOCaptureTestCase(test.TestCase):

    def test_stdout_capture(self):
        stdout = sys.stdout
        messages = ["abcdef", "defgaga"]
        with utils.StdOutCapture() as out:
            for msg in messages:
                print(msg)

        self.assertEqual(out.getvalue().rstrip("\n").split("\n"), messages)
        self.assertEqual(stdout, sys.stdout)

    def test_stderr_capture(self):
        stderr = sys.stderr
        messages = ["abcdef", "defgaga"]
        with utils.StdErrCapture() as err:
            for msg in messages:
                print(msg, file=sys.stderr)

        self.assertEqual(err.getvalue().rstrip("\n").split("\n"), messages)
        self.assertEqual(stderr, sys.stderr)


class TimerTestCase(test.TestCase):

    def test_timer_duration(self):
        start_time = time.time()
        end_time = time.time()

        with mock.patch("rally.common.utils.time") as mock_time:
            mock_time.time = mock.MagicMock(return_value=start_time)
            with utils.Timer() as timer:
                mock_time.time = mock.MagicMock(return_value=end_time)

        self.assertIsNone(timer.error)
        self.assertEqual(start_time, timer.timestamp())
        self.assertEqual(end_time, timer.finish_timestamp())
        self.assertEqual(end_time - start_time, timer.duration())

    def test_timer_exception(self):
        try:
            with utils.Timer() as timer:
                raise Exception()
        except Exception:
            pass
        self.assertEqual(3, len(timer.error))
        self.assertEqual(timer.error[0], type(Exception()))


def module_level_method():
    pass


class MethodClassTestCase(test.TestCase):

    @testtools.skipIf(sys.version_info > (2, 9), "Problems with access to "
                                                 "class from <locals>")
    def test_method_class_for_class_level_method(self):
        class A(object):
            def m(self):
                pass
        self.assertEqual(A, utils.get_method_class(A.m))

    def test_method_class_for_module_level_method(self):
        self.assertIsNone(utils.get_method_class(module_level_method))


class FirstIndexTestCase(test.TestCase):

    def test_list_with_existing_matching_element(self):
        lst = [1, 3, 5, 7]
        self.assertEqual(utils.first_index(lst, lambda e: e == 1), 0)
        self.assertEqual(utils.first_index(lst, lambda e: e == 5), 2)
        self.assertEqual(utils.first_index(lst, lambda e: e == 7), 3)

    def test_list_with_non_existing_matching_element(self):
        lst = [1, 3, 5, 7]
        self.assertIsNone(utils.first_index(lst, lambda e: e == 2))


class EditDistanceTestCase(test.TestCase):

    def test_distance_empty_strings(self):
        dist = utils.distance("", "")
        self.assertEqual(0, dist)

    def test_distance_equal_strings(self):
        dist = utils.distance("abcde", "abcde")
        self.assertEqual(0, dist)

    def test_distance_replacement(self):
        dist = utils.distance("abcde", "__cde")
        self.assertEqual(2, dist)

    def test_distance_insertion(self):
        dist = utils.distance("abcde", "ab__cde")
        self.assertEqual(2, dist)

    def test_distance_deletion(self):
        dist = utils.distance("abcde", "abc")
        self.assertEqual(2, dist)


class TenantIteratorTestCase(test.TestCase):

    def test_iterate_per_tenant(self):
        users = []
        tenants_count = 2
        users_per_tenant = 5
        for tenant_id in range(tenants_count):
            for user_id in range(users_per_tenant):
                users.append({"id": str(user_id),
                              "tenant_id": str(tenant_id)})

        expected_result = [
            ({"id": "0", "tenant_id": str(i)}, str(i)) for i in range(
                tenants_count)]
        real_result = [i for i in utils.iterate_per_tenants(users)]

        self.assertEqual(expected_result, real_result)


class RAMIntTestCase(test.TestCase):

    def test__int__(self):
        self.assertEqual(0, int(utils.RAMInt()))
        self.assertEqual(10, int(utils.RAMInt(10)))

    def test__str__(self):
        self.assertEqual("0", str(utils.RAMInt()))
        self.assertEqual("20", str(utils.RAMInt(20)))

    def test__next__(self):
        ri = utils.RAMInt()
        for i in range(0, 3):
            self.assertEqual(i, next(ri))

    def test_next(self):
        ri = utils.RAMInt()
        for i in range(0, 3):
            self.assertEqual(i, ri.next())

    def test_reset(self):
        ri = utils.RAMInt()
        ri.next()
        ri.reset()
        self.assertEqual(0, int(ri))


@ddt.ddt
class RandomNameTestCase(test.TestCase):

    @ddt.data(
        {},
        {"task_id": "fake-task"},
        {"task_id": "2short", "expected": "s_rally_blargles_dweebled"},
        {"task_id": "fake!task",
         "expected": "s_rally_blargles_dweebled"},
        {"fmt": "XXXX-test-XXX-test",
         "expected": "fake-test-bla-test"})
    @ddt.unpack
    @mock.patch("random.choice")
    def test_generate_random_name(self, mock_choice, task_id="faketask",
                                  expected="s_rally_faketask_blargles",
                                  fmt="s_rally_XXXXXXXX_XXXXXXXX"):
        class FakeNameGenerator(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = fmt
            task = {"uuid": task_id}

        generator = FakeNameGenerator()

        mock_choice.side_effect = iter("blarglesdweebled")
        self.assertEqual(generator.generate_random_name(), expected)

        class FakeNameGenerator(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = fmt
            verification = {"uuid": task_id}

        generator = FakeNameGenerator()

        mock_choice.side_effect = iter("blarglesdweebled")
        self.assertEqual(generator.generate_random_name(), expected)

    def test_generate_random_name_bogus_name_format(self):
        class FakeNameGenerator(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = "invalid_XXX_format"
            task = {"uuid": "fake-task-id"}

        generator = FakeNameGenerator()
        self.assertRaises(ValueError,
                          generator.generate_random_name)

    @ddt.data(
        {"good": ("rally_abcdefgh_abcdefgh", "rally_12345678_abcdefgh",
                  "rally_ABCdef12_ABCdef12"),
         "bad": ("rally_abcd_efgh", "rally_abcd!efg_12345678",
                 "rally_", "rally__", "rally_abcdefgh_",
                 "rally_abcdefghi_12345678", "foo", "foo_abcdefgh_abcdefgh")},
        {"task_id": "abcd1234",
         "good": ("rally_abcd1234_abcdefgh", "rally_abcd1234_abcd1234",
                  "rally_abcd1234_AbCdEf12"),
         "bad": ("rally_12345678_abcdefgh", "rally_12345678_abcd1234",
                 "rally_abcd1234_", "rally_abcd1234_!!!!!!!!",
                 "rally_ABCD1234_abcdefgh")},
        {"task_id": "abcd1234",
         "exact": False,
         "good": ("rally_abcd1234_abcdefghfoo", "rally_abcd1234_abcdefgh",
                  "rally_abcd1234_abcdefgh-bar",
                  "rally_abcd1234_abcdefgh+!@$"),
         "bad": ("rally_abcd1234_", "rally_abcd1234_!!!!!!!!",
                 "rally_abcd1234_abcdefg")},
        {"fmt": "][*_XXX_XXX",
         "chars": "abc(.*)",
         "good": ("][*_abc_abc", "][*_abc_((("),
         "bad": ("rally_ab_cd", "rally_ab!_abc", "rally_", "rally__",
                 "rally_abc_", "rally_abcd_abc", "foo", "foo_abc_abc")},
        {"fmt": "XXXX-test-XXX-test",
         "good": ("abcd-test-abc-test",),
         "bad": ("rally-abcdefgh-abcdefgh", "abc-test-abc-test",
                 "abcd_test_abc_test", "abc-test-abcd-test")})
    @ddt.unpack
    def test_cls_name_matches_object(
            self, good=(), bad=(), fmt="rally_XXXXXXXX_XXXXXXXX",
            chars=string.ascii_letters + string.digits, task_id=None,
            exact=True):
        class FakeNameGenerator(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = fmt
            RESOURCE_NAME_ALLOWED_CHARACTERS = chars
            task = {"uuid": task_id or "fakeuuid"}

        for name in good:
            self.assertTrue(
                FakeNameGenerator.name_matches_object(name, task_id, exact),
                "%(name)s unexpectedly didn't match RESOURCE_NAME_FORMAT "
                "%(fmt)s with exact=%(exact)s" %
                {"name": name, "fmt": fmt, "exact": exact})

        for name in bad:
            self.assertFalse(
                FakeNameGenerator.name_matches_object(name, task_id, exact),
                "%(name)s unexpectedly matched RESOURCE_NAME_FORMAT %(fmt)s "
                "with exact=%(exact)s" %
                {"name": name, "fmt": fmt, "exact": exact})

    def test_name_matches_object(self):
        name = "foo"
        obj = mock.Mock()
        self.assertTrue(utils.name_matches_object(name, obj))
        obj.name_matches_object.assert_called_once_with(name)

    def test_name_matches_object_kwargs(self):
        name = "foo"
        obj = mock.Mock()
        self.assertTrue(utils.name_matches_object(name, obj, task_id="taskid",
                                                  exact=False))
        obj.name_matches_object.assert_called_once_with(name, task_id="taskid",
                                                        exact=False)

    def test_name_matches_object_identical_list(self):
        class One(utils.RandomNameGeneratorMixin):
            name_matches_object = mock.Mock(return_value=False)

        class Two(utils.RandomNameGeneratorMixin):
            name_matches_object = mock.Mock(return_value=False)

        name = "foo"
        self.assertFalse(utils.name_matches_object(name, One, Two))
        # ensure that exactly one of the two objects is checked
        self.assertItemsEqual(
            One.name_matches_object.call_args_list +
            Two.name_matches_object.call_args_list,
            [mock.call(name)])

    def test_name_matches_object_differing_list(self):
        class One(utils.RandomNameGeneratorMixin):
            name_matches_object = mock.Mock(return_value=False)

        class Two(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = "foo_XXX_XXX"
            name_matches_object = mock.Mock(return_value=False)

        class Three(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_ALLOWED_CHARACTERS = "12345"
            name_matches_object = mock.Mock(return_value=False)

        class Four(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = "bar_XXX_XXX"
            RESOURCE_NAME_ALLOWED_CHARACTERS = "abcdef"
            name_matches_object = mock.Mock(return_value=False)

        classes = (One, Two, Three, Four)
        name = "foo"
        self.assertFalse(utils.name_matches_object(name, *classes))
        for cls in classes:
            cls.name_matches_object.assert_called_once_with(name)

    def test_cls_name_matches_object_identity(self):
        generator = utils.RandomNameGeneratorMixin()
        generator.task = {"uuid": "faketask"}

        self.assertTrue(generator.name_matches_object(
            generator.generate_random_name()))
        self.assertTrue(utils.RandomNameGeneratorMixin.name_matches_object(
            generator.generate_random_name()))

    def test_name_matches_object_identity(self):
        generator = utils.RandomNameGeneratorMixin()
        generator.task = {"uuid": "faketask"}

        self.assertTrue(utils.name_matches_object(
            generator.generate_random_name(), generator))
        self.assertTrue(utils.name_matches_object(
            generator.generate_random_name(), utils.RandomNameGeneratorMixin))

    def test_consistent_task_id_part(self):
        class FakeNameGenerator(utils.RandomNameGeneratorMixin):
            RESOURCE_NAME_FORMAT = "XXXXXXXX_XXXXXXXX"

        generator = FakeNameGenerator()
        generator.task = {"uuid": "good-task-id"}

        names = [generator.generate_random_name() for i in range(100)]
        task_id_parts = set([n.split("_")[0] for n in names])
        self.assertEqual(len(task_id_parts), 1)

        generator.task = {"uuid": "bogus! task! id!"}

        names = [generator.generate_random_name() for i in range(100)]
        task_id_parts = set([n.split("_")[0] for n in names])
        self.assertEqual(len(task_id_parts), 1)


@ddt.ddt
class MergeTestCase(test.TestCase):
    @ddt.data(
        # regular data
        {"sources": [[[1, 3, 5], [5, 7, 9, 14], [17, 21, 36, 41]],
                     [[2, 2, 4], [9, 10], [16, 19, 23, 26, 91]],
                     [[5], [5, 7, 11, 14, 14, 19, 23]]],
         "expected_output": [[1, 2, 2, 3, 4, 5, 5, 5, 5, 7],
                             [7, 9, 9, 10, 11, 14, 14, 14, 16, 17],
                             [19, 19, 21, 23, 23, 26, 36, 41, 91]]},
        # with one empty source
        {"sources": [[[1, 3, 5], [5, 7, 9, 14], [17, 21, 36, 41]],
                     [[2, 2, 4], [9, 10], [16, 19, 23, 26, 91]],
                     [[5], [5, 7, 11, 14, 14, 19, 23]],
                     []],
         "expected_output": [[1, 2, 2, 3, 4, 5, 5, 5, 5, 7],
                             [7, 9, 9, 10, 11, 14, 14, 14, 16, 17],
                             [19, 19, 21, 23, 23, 26, 36, 41, 91]]},
        # with one source that produces an empty list
        {"sources": [[[1, 3, 5], [5, 7, 9, 14], [17, 21, 36, 41]],
                     [[2, 2, 4], [9, 10], [16, 19, 23, 26, 91]],
                     [[5], [5, 7, 11, 14, 14, 19, 23]],
                     [[]]],
         "expected_output": [[1, 2, 2, 3, 4, 5, 5, 5, 5, 7],
                             [7, 9, 9, 10, 11, 14, 14, 14, 16, 17],
                             [19, 19, 21, 23, 23, 26, 36, 41, 91]]},
        # with empty lists appered in sources
        {"sources": [[[1, 3, 5], [], [], [5, 7, 9, 14], [17, 21, 36, 41]],
                     [[], [2, 2, 4], [9, 10], [16, 19, 23, 26, 91]],
                     [[5], [5, 7, 11, 14, 14, 19, 23], []]],
         "expected_output": [[1, 2, 2, 3, 4, 5, 5, 5, 5, 7],
                             [7, 9, 9, 10, 11, 14, 14, 14, 16, 17],
                             [19, 19, 21, 23, 23, 26, 36, 41, 91]]},
        # only one source
        {"sources": [[[1, 3, 5], [5, 7, 9, 14], [17, 21, 36, 41]]],
         "expected_output": [[1, 3, 5, 5, 7, 9, 14, 17, 21, 36], [41]]},
        # no sources passed in
        {"sources": [],
         "expected_output": []},
        # several sources, all empty
        {"sources": [[], [], [], []],
         "expected_output": []}

    )
    @ddt.unpack
    def test_merge(self, sources, expected_output):
        in_iters = [iter(src) for src in sources]

        out = list(utils.merge(10, *in_iters))
        self.assertEqual(out, expected_output)


class TimeoutThreadTestCase(test.TestCase):
    def test_timeout_thread(self):
        """Create and kill thread by timeout.

        This single test covers 3 methods: terminate_thread, timeout_thread,
        and interruptable_sleep.

        This test is more like integrated then unit, but it is much better
        then unreadable 500 lines of mocking and checking.
        """
        queue = Queue.Queue()
        killer_thread = threading.Thread(
            target=utils.timeout_thread,
            args=(queue,),
        )
        test_thread = threading.Thread(
            target=utils.interruptable_sleep,
            args=(30, 0.01),
        )
        test_thread.start()
        start_time = time.time()
        queue.put((test_thread, start_time + 1))
        killer_thread.start()
        test_thread.join()
        end_time = time.time()
        queue.put((None, None))
        killer_thread.join()
        time_elapsed = end_time - start_time
        # NOTE(sskripnick): Killing thread with PyThreadState_SetAsyncExc
        # works with sinificant delay. Make sure this delay is less
        # than 10 seconds.
        self.assertLess(time_elapsed, 11,
                        "Thread killed too late (%s seconds)" % time_elapsed)


class LockedDictTestCase(test.TestCase):

    def test_init_unlock_and_update(self):
        def setitem(obj, key, value):
            obj[key] = value

        def delitem(obj, key):
            del obj[key]

        d = utils.LockedDict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d, {})

        d = utils.LockedDict(foo="bar", spam={"a": ["b", {"c": "d"}]})
        self.assertEqual(d, {"foo": "bar", "spam": {"a": ("b", {"c": "d"})}})
        self.assertIsInstance(d["spam"], utils.LockedDict)
        self.assertIsInstance(d["spam"]["a"][1], utils.LockedDict)
        self.assertRaises(RuntimeError, setitem, d, 123, 456)
        self.assertRaises(RuntimeError, delitem, d, "foo")
        self.assertRaises(RuntimeError, setitem, d["spam"]["a"][1], 123, 456)
        self.assertRaises(RuntimeError, delitem, d["spam"]["a"][1], "c")
        self.assertRaises(RuntimeError, d.update, {123: 456})
        self.assertRaises(RuntimeError, d.setdefault, 123, 456)
        self.assertRaises(RuntimeError, d.pop, "foo")
        self.assertRaises(RuntimeError, d.popitem)
        self.assertRaises(RuntimeError, d.clear)
        self.assertEqual(d, {"foo": "bar", "spam": {"a": ("b", {"c": "d"})}})

        with d.unlocked():
            d["spam"] = 42
            self.assertEqual(d, {"foo": "bar", "spam": 42})
            d.clear()
            self.assertEqual(d, {})
            d.setdefault("foo", 42)
            d.update({"bar": 24})
            self.assertEqual(d, {"foo": 42, "bar": 24})
            self.assertEqual(24, d.pop("bar"))
            self.assertEqual(("foo", 42), d.popitem())
            d[123] = 456

        self.assertEqual(d, {123: 456})

        self.assertRaises(RuntimeError, setitem, d, 123, 456)
        self.assertRaises(RuntimeError, delitem, d, "foo")

    @mock.patch("rally.common.utils.copy.deepcopy")
    def test___deepcopy__(self, mock_deepcopy):
        mock_deepcopy.side_effect = lambda *args, **kw: (args, kw)
        d = utils.LockedDict(foo="bar", spam={"a": ["b", {"c": "d"}]})
        args, kw = d.__deepcopy__()
        self.assertEqual({"memo": None}, kw)
        self.assertEqual(({"foo": "bar", "spam": {"a": ("b", {"c": "d"})}},),
                         args)
        self.assertEqual(dict, type(args[0]))
        self.assertEqual(dict, type(args[0]["spam"]))
        self.assertEqual(dict, type(args[0]["spam"]["a"][1]))

        mock_deepcopy.reset_mock()
        args, kw = d.__deepcopy__("foo_memo")
        self.assertEqual(({"foo": "bar", "spam": {"a": ("b", {"c": "d"})}},),
                         args)
        self.assertEqual({"memo": "foo_memo"}, kw)


@ddt.ddt
class FloatFormatterTestCase(test.TestCase):

    @ddt.data(
        {
            "num_float": 0,
            "num_str": "0.0"
        },
        {
            "num_float": 37,
            "num_str": "37.0"
        },
        {
            "num_float": 0.0000001,
            "num_str": "0.0"
        },
        {
            "num_float": 0.000000,
            "num_str": "0.0"
        },
        {
            "num_float": 1.0000001,
            "num_str": "1.0"
        },
        {
            "num_float": 1.0000011,
            "num_str": "1.000001"
        },
        {
            "num_float": 1.0000019,
            "num_str": "1.000002"
        }

    )
    @ddt.unpack
    def test_format_float_to_str(self, num_float, num_str):
        self.assertEqual(num_str, utils.format_float_to_str(num_float))


class DequeAsQueueTestCase(test.TestCase):

    def setUp(self):
        super(DequeAsQueueTestCase, self).setUp()
        self.deque = collections.deque()
        self.deque_as_queue = utils.DequeAsQueue(self.deque)

    def test_qsize(self):
        self.assertEqual(0, self.deque_as_queue.qsize())
        self.deque.append(10)
        self.assertEqual(1, self.deque_as_queue.qsize())

    def test_put(self):
        self.deque_as_queue.put(10)
        self.assertEqual(10, self.deque.popleft())

    def test_get(self):
        self.deque.append(33)
        self.assertEqual(33, self.deque_as_queue.get())

    def test_empty(self):
        self.assertFalse(self.deque_as_queue.empty())
        self.deque.append(10)
        self.assertTrue(self.deque_as_queue.empty())


class StopwatchTestCase(test.TestCase):

    @mock.patch("rally.common.utils.interruptable_sleep")
    @mock.patch("rally.common.utils.time")
    def test_stopwatch(self, mock_time, mock_interruptable_sleep):
        mock_time.time.side_effect = [0, 0, 1, 2, 3]

        sw = utils.Stopwatch()
        sw.start()
        sw.sleep(1)
        sw.sleep(2)
        sw.sleep(3)

        mock_interruptable_sleep.assert_has_calls([
            mock.call(1),
            mock.call(1),
            mock.call(1),
        ])

    @mock.patch("rally.common.utils.interruptable_sleep")
    @mock.patch("rally.common.utils.time")
    def test_no_sleep(self, mock_time, mock_interruptable_sleep):
        mock_time.time.side_effect = [0, 1]

        sw = utils.Stopwatch()
        sw.start()
        sw.sleep(1)

        self.assertFalse(mock_interruptable_sleep.called)

    @mock.patch("rally.common.utils.time")
    def test_stopwatch_with_event(self, mock_time):
        mock_time.time.side_effect = [0, 0, 1, 2, 3]
        event = mock.Mock(spec=threading.Event)()

        sw = utils.Stopwatch(stop_event=event)
        sw.start()
        sw.sleep(1)
        sw.sleep(2)
        sw.sleep(3)

        event.wait.assert_has_calls([
            mock.call(1),
            mock.call(1),
            mock.call(1),
        ])
