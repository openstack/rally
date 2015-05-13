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

import datetime

import mock

from rally.benchmark import utils
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class BenchmarkUtilsTestCase(test.TestCase):

    def test_wait_for_delete(self):
        def update_resource(self):
            raise exceptions.GetResourceNotFound()

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
        class service():
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
        class service():
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
        deadline = datetime.datetime.now() + datetime.timedelta(**delay)
        return lambda obj: datetime.datetime.now() > deadline

    def fake_checker_false(self, obj):
        return False

    def fake_updater(self, obj):
        return obj

    def test_wait_for_with_updater(self):
        loaded_resource = utils.wait_for(self.resource,
                                         self.fake_checker_delayed,
                                         self.fake_updater,
                                         1, self.load_secs / 3)
        self.assertEqual(loaded_resource, self.resource)

    def test_wait_for_no_updater(self):
        loaded_resource = utils.wait_for(self.resource,
                                         self.fake_checker_delayed,
                                         None, 1, self.load_secs / 3)
        self.assertEqual(loaded_resource, self.resource)

    def test_wait_for_timeout_failure(self):
        self.resource.name = "fake_name"
        self.resource.id = "fake_id"
        self.resource.status = "fake_stale_status"

        is_ready = utils.resource_is("fake_new_status")
        exc = self.assertRaises(
            exceptions.TimeoutException, utils.wait_for,
            self.resource, is_ready,
            self.fake_updater, self.load_secs,
            self.load_secs / 3)

        self.assertEqual(exc.kwargs["resource_name"], "fake_name")
        self.assertEqual(exc.kwargs["resource_id"], "fake_id")
        self.assertEqual(exc.kwargs["desired_status"], "fake_new_status")
        self.assertEqual(exc.kwargs["resource_status"], "FAKE_STALE_STATUS")

        self.assertIn("FakeResource", str(exc))
        self.assertIn("fake_new_status", str(exc))
