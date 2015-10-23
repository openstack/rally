# Copyright 2013: Mirantis Inc.
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

from __future__ import print_function
import string
import sys
import time

import ddt
import mock
import testtools

from rally.common.i18n import _
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
        self.assertEqual(end_time - start_time, timer.duration())

    def test_timer_exception(self):
        try:
            with utils.Timer() as timer:
                raise Exception()
        except Exception:
            pass
        self.assertEqual(3, len(timer.error))
        self.assertEqual(timer.error[0], type(Exception()))


class LogTestCase(test.TestCase):

    def test_log_task_wrapper(self):
        mock_log = mock.MagicMock()
        msg = "test %(a)s %(b)s"

        class TaskLog(object):

            def __init__(self):
                self.task = {"uuid": "some_uuid"}

            @utils.log_task_wrapper(mock_log, msg, a=10, b=20)
            def some_method(self, x, y):
                return x + y

        t = TaskLog()
        self.assertEqual(t.some_method.__name__, "some_method")
        self.assertEqual(t.some_method(2, 2), 4)
        params = {"msg": msg % {"a": 10, "b": 20}, "uuid": t.task["uuid"]}
        expected = [
            mock.call(_("Task %(uuid)s | Starting:  %(msg)s") % params),
            mock.call(_("Task %(uuid)s | Completed: %(msg)s") % params)
        ]
        self.assertEqual(mock_log.mock_calls, expected)

    def test_log_deprecated(self):
        mock_log = mock.MagicMock()

        @utils.log_deprecated("some alternative", "0.0.1", mock_log)
        def some_method(x, y):
            return x + y

        self.assertEqual(some_method(2, 2), 4)
        mock_log.assert_called_once_with("'some_method' is deprecated in "
                                         "Rally v0.0.1: some alternative")

    def test_log_deprecated_args(self):
        mock_log = mock.MagicMock()

        @utils.log_deprecated_args("Deprecated test", "0.0.1", ("z",),
                                   mock_log, once=True)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")

        mock_log.reset_mock()
        self.assertEqual(some_method(2, 2, z=3), 7)
        self.assertFalse(mock_log.called)

        @utils.log_deprecated_args("Deprecated test", "0.0.1", ("z",),
                                   mock_log, once=False)
        def some_method(x, y, z):
            return x + y + z

        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")

        mock_log.reset_mock()
        self.assertEqual(some_method(2, 2, z=3), 7)
        mock_log.assert_called_once_with(
            "Deprecated test (args `z' deprecated in Rally v0.0.1)")


def module_level_method():
    pass


class MethodClassTestCase(test.TestCase):

    @testtools.skipIf(sys.version_info > (2, 9), "Problems with access to "
                                                 "class from <locals>")
    def test_method_class_for_class_level_method(self):
        class A:
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

    @mock.patch("rally.common.utils.multiprocessing")
    def test__init__(self, mock_multiprocessing):
        utils.RAMInt()
        mock_multiprocessing.Lock.assert_called_once_with()
        mock_multiprocessing.Value.assert_called_once_with("I", 0)

    @mock.patch("rally.common.utils.multiprocessing")
    def test__int__(self, mock_multiprocessing):
        mock_multiprocessing.Value.return_value = mock.Mock(value=42)
        self.assertEqual(int(utils.RAMInt()), 42)

    @mock.patch("rally.common.utils.multiprocessing")
    def test__str__(self, mock_multiprocessing):
        mock_multiprocessing.Value.return_value = mock.Mock(value=42)
        self.assertEqual(str(utils.RAMInt()), "42")

    @mock.patch("rally.common.utils.multiprocessing")
    def test__iter__(self, mock_multiprocessing):
        ram_int = utils.RAMInt()
        self.assertEqual(iter(ram_int), ram_int)

    @mock.patch("rally.common.utils.multiprocessing")
    def test__next__(self, mock_multiprocessing):
        class MemInt(int):
            THRESHOLD = 5

            def __iadd__(self, i):
                return MemInt((int(self) + i) % self.THRESHOLD)

        mock_lock = mock.MagicMock()
        mock_multiprocessing.Lock.return_value = mock_lock
        mock_multiprocessing.Value.return_value = mock.Mock(value=MemInt(0))

        ram_int = utils.RAMInt()
        self.assertEqual(int(ram_int), 0)
        for i in range(MemInt.THRESHOLD - 1):
            self.assertEqual(ram_int.__next__(), i)
        self.assertRaises(StopIteration, ram_int.__next__)
        self.assertEqual(mock_lock.__enter__.mock_calls,
                         [mock.call()] * MemInt.THRESHOLD)
        self.assertEqual(len(mock_lock.__exit__.mock_calls), MemInt.THRESHOLD)

    @mock.patch("rally.common.utils.RAMInt.__next__",
                return_value="next_value")
    @mock.patch("rally.common.utils.multiprocessing")
    def test_next(self, mock_multiprocessing, mock_ram_int___next__):
        self.assertEqual(next(utils.RAMInt()), "next_value")
        mock_ram_int___next__.assert_called_once_with()

    @mock.patch("rally.common.utils.multiprocessing")
    def test_reset(self, mock_multiprocessing):
        ram_int = utils.RAMInt()
        self.assertRaises(TypeError, int, ram_int)
        ram_int.reset()
        self.assertEqual(int(ram_int), 0)


class GenerateRandomTestCase(test.TestCase):

    @mock.patch("rally.common.utils.random")
    def test_generate_random_name(self, mock_random):
        choice = "foobarspamchoicestring"

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(utils.generate_random_name(),
                         string.ascii_lowercase[:16])

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(utils.generate_random_name(length=10),
                         string.ascii_lowercase[:10])

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(utils.generate_random_name(choice=choice),
                         choice[:16])

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(utils.generate_random_name(choice=choice, length=5),
                         choice[:5])

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(
            utils.generate_random_name(prefix="foo_", length=10),
            "foo_" + string.ascii_lowercase[:10])

        idx = iter(range(100))
        mock_random.choice.side_effect = lambda choice: choice[next(idx)]
        self.assertEqual(
            utils.generate_random_name(prefix="foo_",
                                       choice=choice, length=10),
            "foo_" + choice[:10])


@ddt.ddt
class RandomNameTestCase(test.TestCase):

    @ddt.data(
        {},
        {"task_id": "fake-task"},
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
    def test_name_matches_pattern(self, good=(), bad=(),
                                  fmt="rally_XXXXXXXX_XXXXXXXX",
                                  chars=string.ascii_letters + string.digits):
        for name in good:
            self.assertTrue(
                utils.name_matches_pattern(name, fmt, chars),
                "%s unexpectedly didn't match resource_name_format" % name)

        for name in bad:
            self.assertFalse(
                utils.name_matches_pattern(name, fmt, chars),
                "%s unexpectedly matched resource_name_format" % name)

    @mock.patch("rally.common.utils.name_matches_pattern")
    def test_name_matches_object(self, mock_name_matches_pattern):
        name = "foo"
        self.assertEqual(
            utils.name_matches_object(name,
                                      utils.RandomNameGeneratorMixin),
            mock_name_matches_pattern.return_value)
        mock_name_matches_pattern.assert_called_once_with(
            name,
            utils. RandomNameGeneratorMixin.RESOURCE_NAME_FORMAT,
            utils.RandomNameGeneratorMixin.RESOURCE_NAME_ALLOWED_CHARACTERS)

    def test_name_matches_pattern_identity(self):
        generator = utils.RandomNameGeneratorMixin()
        generator.task = {"uuid": "faketask"}

        self.assertTrue(utils.name_matches_pattern(
            generator.generate_random_name(),
            generator.RESOURCE_NAME_FORMAT,
            generator.RESOURCE_NAME_ALLOWED_CHARACTERS))

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
