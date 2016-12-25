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

import datetime as dt

from jsonschema import exceptions as schema_exceptions
import mock

from rally import exceptions
from rally.task import utils
from tests.unit import fakes
from tests.unit import test


class BenchmarkUtilsTestCase(test.TestCase):

    def test_wait_for_delete(self):
        def update_resource(self):
            raise exceptions.GetResourceNotFound(resource=None)

        resource = mock.MagicMock()
        utils.wait_for_delete(resource, update_resource=update_resource)

    @mock.patch("time.sleep")
    @mock.patch("time.time")
    def test_wait_for_delete_fails(self, mock_time, mock_sleep):
        def update_resource(self):
            pass

        mock_time.side_effect = [1, 2, 3, 4]
        resource = mock.MagicMock()
        self.assertRaises(exceptions.TimeoutException, utils.wait_for_delete,
                          resource, update_resource=update_resource,
                          timeout=1)

    def test_resource_is(self):
        is_active = utils.resource_is("ACTIVE")
        self.assertEqual(is_active.status_getter, utils.get_status)
        self.assertTrue(is_active(fakes.FakeResource(status="active")))
        self.assertTrue(is_active(fakes.FakeResource(status="aCtIvE")))
        self.assertFalse(is_active(fakes.FakeResource(status="ERROR")))

    def test_resource_is_with_fake_status_getter(self):
        fake_getter = mock.MagicMock(return_value="LGTM")
        fake_res = mock.MagicMock()
        is_lgtm = utils.resource_is("LGTM", fake_getter)
        self.assertTrue(is_lgtm(fake_res))
        fake_getter.assert_called_once_with(fake_res)

    def test_infinite_run_args_generator(self):
        args = lambda x: (x, "a", "b", 123)
        for i, real_args in enumerate(utils.infinite_run_args_generator(args)):
            self.assertEqual((i, "a", "b", 123), real_args)
            if i > 5:
                break

    def test_manager_list_sizes(self):
        manager = fakes.FakeManager()

        def lst():
            return [1] * 10

        manager.list = lst
        manager_list_size = utils.manager_list_size([5])
        self.assertFalse(manager_list_size(manager))

        manager_list_size = utils.manager_list_size([10])
        self.assertTrue(manager_list_size(manager))

    def test_get_from_manager(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager)
        manager._cache(resource)
        self.assertEqual(get_from_manager(resource), resource)

    def test_get_from_manager_with_uuid_field(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager)
        manager._cache(resource)
        self.assertEqual(get_from_manager(resource, id_attr="uuid"), resource)

    def test_get_from_manager_in_error_state(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager, status="ERROR")
        manager._cache(resource)
        self.assertRaises(exceptions.GetResourceFailure,
                          get_from_manager, resource)

    def test_get_from_manager_in_deleted_state(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager, status="DELETED")
        manager._cache(resource)
        self.assertRaises(exceptions.GetResourceNotFound,
                          get_from_manager, resource)

    def test_get_from_manager_in_deleted_state_for_heat_resource(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager)
        resource.stack_status = "DELETE_COMPLETE"
        manager._cache(resource)
        self.assertRaises(exceptions.GetResourceNotFound,
                          get_from_manager, resource)

    def test_get_from_manager_in_deleted_state_for_ceilometer_resource(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager)
        resource.state = "DELETED"
        manager._cache(resource)
        self.assertRaises(exceptions.GetResourceNotFound,
                          get_from_manager, resource)

    def test_get_from_manager_not_found(self):
        get_from_manager = utils.get_from_manager()
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class NotFoundException(Exception):
            http_status = 404

        manager.get = mock.MagicMock(side_effect=NotFoundException)
        self.assertRaises(exceptions.GetResourceNotFound,
                          get_from_manager, resource)

    def test_get_from_manager_http_exception(self):
        get_from_manager = utils.get_from_manager()
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class HTTPException(Exception):
            pass

        manager.get = mock.MagicMock(side_effect=HTTPException)
        self.assertRaises(exceptions.GetResourceFailure,
                          get_from_manager, resource)

    def test_check_service_status(self):
        class service(object):
            def __init__(self, name):
                self.status = "enabled"
                self.state = "up"
                self.name = name

            def __str__(self):
                return self.name

        client = mock.MagicMock()
        client.services.list.return_value = [service("nova-compute"),
                                             service("nova-network"),
                                             service("glance-api")]
        ret = utils.check_service_status(client, "nova-network")
        self.assertTrue(ret)
        self.assertTrue(client.services.list.called)

    def test_check_service_status_fail(self):
        class service(object):
            def __init__(self, name):
                self.status = "enabled"
                self.state = "down"
                self.name = name

            def __str__(self):
                return self.name

        client = mock.MagicMock()
        client.services.list.return_value = [service("nova-compute"),
                                             service("nova-network"),
                                             service("glance-api")]
        ret = utils.check_service_status(client, "nova-network")
        self.assertFalse(ret)
        self.assertTrue(client.services.list.called)


class WaitForTestCase(test.TestCase):

    def setUp(self):
        super(WaitForTestCase, self).setUp()

        self.resource = fakes.FakeResource()
        self.load_secs = 0.01
        self.fake_checker_delayed = self.get_fake_checker_delayed(
            seconds=self.load_secs)

    def get_fake_checker_delayed(self, **delay):
        deadline = dt.datetime.now() + dt.timedelta(**delay)
        return lambda obj: dt.datetime.now() > deadline

    def fake_checker_false(self, obj):
        return False

    def fake_updater(self, obj):
        return obj

    def test_wait_for_with_updater(self):
        loaded_resource = utils.wait_for(self.resource,
                                         is_ready=self.fake_checker_delayed,
                                         update_resource=self.fake_updater,
                                         timeout=1,
                                         check_interval=self.load_secs / 3)
        self.assertEqual(loaded_resource, self.resource)

    def test_wait_for_no_updater(self):
        loaded_resource = utils.wait_for(self.resource,
                                         is_ready=self.fake_checker_delayed,
                                         update_resource=None, timeout=1,
                                         check_interval=self.load_secs / 3)
        self.assertEqual(loaded_resource, self.resource)

    def test_wait_for_timeout_failure(self):
        self.resource.name = "fake_name"
        self.resource.id = "fake_id"
        self.resource.status = "fake_stale_status"

        is_ready = utils.resource_is("fake_new_status")
        exc = self.assertRaises(
            exceptions.TimeoutException, utils.wait_for,
            self.resource, is_ready=is_ready,
            update_resource=self.fake_updater, timeout=self.load_secs,
            check_interval=self.load_secs / 3)

        self.assertEqual(exc.kwargs["resource_name"], "fake_name")
        self.assertEqual(exc.kwargs["resource_id"], "fake_id")
        self.assertEqual(exc.kwargs["desired_status"], "fake_new_status")
        self.assertEqual(exc.kwargs["resource_status"], "FAKE_STALE_STATUS")

        self.assertIn("FakeResource", str(exc))
        self.assertIn("fake_new_status", str(exc))


def action_one(self, *args, **kwargs):
    pass


def action_two(self, *args, **kwargs):
    pass


class ActionBuilderTestCase(test.TestCase):

    def setUp(self):
        super(ActionBuilderTestCase, self).setUp()
        self.mock_one = "%s.action_one" % __name__
        self.mock_two = "%s.action_two" % __name__

    def test_invalid_keyword(self):
        builder = utils.ActionBuilder(["action_one", "action_two"])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.build_actions, [{"missing": 1}])

    def test_invalid_bind(self):
        builder = utils.ActionBuilder(["action_one"])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.bind_action, "missing", action_one)

    def test_invalid_schema(self):
        builder = utils.ActionBuilder(["action_one", "action_two"])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{"action_oone": 1},
                                             {"action_twoo": 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{"action_one": -1},
                                             {"action_two": 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{"action_one": 0},
                                             {"action_two": 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{1: 0},
                                             {"action_two": 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{"action_two": "action_two"}])

    def test_positional_args(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(["action_one", "action_two"])
                builder.bind_action("action_one", mock_action_one, "a", "b")
                builder.bind_action("action_two", mock_action_two, "c")
                actions = builder.build_actions([{"action_two": 3},
                                                 {"action_one": 4}])
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call("a", "b"))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call("c"))
        mock_action_two.assert_has_calls(mock_calls)

        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(["action_one", "action_two"])
                builder.bind_action("action_one", mock_action_one, "a", "b")
                builder.bind_action("action_two", mock_action_two, "c")
                actions = builder.build_actions([{"action_two": 3},
                                                 {"action_one": 4}],
                                                "d", 5)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call("a", "b", "d", 5))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call("c", "d", 5))
        mock_action_two.assert_has_calls(mock_calls)

    def test_kwargs(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(["action_one", "action_two"])
                builder.bind_action("action_one", mock_action_one, a=1, b=2)
                builder.bind_action("action_two", mock_action_two, c=3)
                actions = builder.build_actions([{"action_two": 3},
                                                 {"action_one": 4}])
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call(a=1, b=2))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call(c=3))
        mock_action_two.assert_has_calls(mock_calls)

        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(["action_one", "action_two"])
                builder.bind_action("action_one", mock_action_one, a=1, b=2)
                builder.bind_action("action_two", mock_action_two, c=3)
                actions = builder.build_actions([{"action_two": 3},
                                                 {"action_one": 4}],
                                                d=4, e=5)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call(a=1, b=2, d=4, e=5))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call(c=3, d=4, e=5))
        mock_action_two.assert_has_calls(mock_calls)

    def test_mixed_args(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(["action_one", "action_two"])
                builder.bind_action("action_one", mock_action_one, "one",
                                    a=1, b=2)
                builder.bind_action("action_two", mock_action_two, "two", c=3)
                actions = builder.build_actions([{"action_two": 3},
                                                 {"action_one": 4}],
                                                "three", d=4)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call("one", "three", a=1, b=2, d=4))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call("two", "three", c=3, d=4))
        mock_action_two.assert_has_calls(mock_calls)


class WaitForStatusTestCase(test.TestCase):

    def test_wrong_ready_statuses_type(self):
        self.assertRaises(ValueError,
                          utils.wait_for, {}, ready_statuses="abc")

    def test_wrong_failure_statuses_type(self):
        self.assertRaises(ValueError,
                          utils.wait_for, {}, ready_statuses=["abc"],
                          failure_statuses="abc")

    def test_no_ready_statuses(self):
        self.assertRaises(ValueError,
                          utils.wait_for, {}, ready_statuses=[])

    def test_no_update(self):
        self.assertRaises(ValueError,
                          utils.wait_for, {}, ready_statuses=["ready"])

    @mock.patch("rally.task.utils.time.sleep")
    def test_exit_instantly(self, mock_sleep):
        res = {"status": "ready"}
        upd = mock.MagicMock(return_value=res)

        utils.wait_for(resource=res, ready_statuses=["ready"],
                       update_resource=upd)

        upd.assert_called_once_with(res)
        self.assertFalse(mock_sleep.called)

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", return_value=1)
    def test_wait_successful(self, mock_time, mock_sleep):
        res = {"status": "not_ready"}
        upd = mock.MagicMock(side_effect=[{"status": "not_ready"},
                                          {"status": "not_ready_yet"},
                                          {"status": "still_not_ready"},
                                          {"status": "almost_ready"},
                                          {"status": "ready"}])
        utils.wait_for(resource=res, ready_statuses=["ready"],
                       update_resource=upd)
        upd.assert_has_calls([mock.call({"status": "not_ready"}),
                              mock.call({"status": "not_ready"}),
                              mock.call({"status": "not_ready_yet"}),
                              mock.call({"status": "still_not_ready"}),
                              mock.call({"status": "almost_ready"})])

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", return_value=1)
    def test_wait_successful_with_uuid(self, mock_time, mock_sleep):
        res = {"status": "not_ready"}
        upd = mock.MagicMock(side_effect=[{"status": "not_ready"},
                                          {"status": "not_ready_yet"},
                                          {"status": "still_not_ready"},
                                          {"status": "almost_ready"},
                                          {"status": "ready"}])
        utils.wait_for(resource=res, ready_statuses=["ready"],
                       update_resource=upd, id_attr="uuid")
        upd.assert_has_calls([mock.call({"status": "not_ready"},
                                        id_attr="uuid"),
                              mock.call({"status": "not_ready"},
                                        id_attr="uuid"),
                              mock.call({"status": "not_ready_yet"},
                                        id_attr="uuid"),
                              mock.call({"status": "still_not_ready"},
                                        id_attr="uuid"),
                              mock.call({"status": "almost_ready"},
                                        id_attr="uuid")])

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", return_value=1)
    def test_wait_failure(self, mock_time, mock_sleep):
        res = {"status": "not_ready"}
        upd = mock.MagicMock(side_effect=[{"status": "not_ready"},
                                          {"status": "fail"}])
        self.assertRaises(exceptions.GetResourceErrorStatus, utils.wait_for,
                          resource=res, ready_statuses=["ready"],
                          failure_statuses=["fail"], update_resource=upd)

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", return_value=1)
    def test_wait_deletion_404(self, mock_time, mock_sleep):
        # resource manager returns 404, wait_for_status catch and accept that
        res = mock.MagicMock()
        notfound = exceptions.GetResourceNotFound(resource=None)
        upd = mock.MagicMock(side_effect=notfound)
        ret = utils.wait_for_status(resource=res,
                                    ready_statuses=["deleted"],
                                    check_deletion=True,
                                    update_resource=upd)
        self.assertIsNone(ret)

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", return_value=1)
    def test_wait_deletion_deleted(self, mock_time, mock_sleep):
        # resource manager return resouce with "deleted" status sometime,
        # wait_for_status return the resouce instance.
        res = {"status": "deleted"}
        upd = mock.MagicMock(side_effect=[{"status": "deleted"}])
        ret = utils.wait_for_status(resource=res,
                                    ready_statuses=["deleted"],
                                    check_deletion=True,
                                    update_resource=upd)
        self.assertEqual(res, ret)

    @mock.patch("rally.task.utils.time.sleep")
    @mock.patch("rally.task.utils.time.time", side_effect=[1, 2, 3, 4])
    def test_wait_timeout(self, mock_time, mock_sleep):
        res = {"status": "not_ready"}
        upd = mock.MagicMock(side_effect=[{"status": "not_ready"},
                                          {"status": "fail"}])
        self.assertRaises(exceptions.TimeoutException,
                          utils.wait_for_status,
                          resource=res, ready_statuses=["ready"],
                          update_resource=upd, timeout=2, id_attr="uuid")