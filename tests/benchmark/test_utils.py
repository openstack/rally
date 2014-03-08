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

import mock

import datetime
from tests import fakes
from tests import test

from rally.benchmark import utils
from rally import exceptions


class BenchmarkUtilsTestCase(test.TestCase):

    def test_resource_is(self):
        is_active = utils.resource_is("ACTIVE")
        self.assertTrue(is_active(fakes.FakeResource(status="active")))
        self.assertTrue(is_active(fakes.FakeResource(status="aCtIvE")))
        self.assertFalse(is_active(fakes.FakeResource(status="ERROR")))

    def test_infinite_run_args(self):
        args = ("a", "b", "c", "d", 123)
        for i, real_args in enumerate(utils.infinite_run_args(args)):
            self.assertEqual((i,) + args, real_args)
            if i == 10:
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

    def test_get_from_manager_not_found(self):
        get_from_manager = utils.get_from_manager()
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class NotFoundException(Exception):
            http_status = 404

        manager.get = mock.MagicMock(side_effect=NotFoundException)
        self.assertRaises(exceptions.GetResourceFailure,
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


class WaitForTestCase(test.TestCase):

    def test_wait_for(self):

        def get_fake_checker_delayed(**delay):
            deadline = datetime.datetime.now() + datetime.timedelta(**delay)
            return lambda obj: datetime.datetime.now() > deadline

        def fake_checker_false(obj):
            return False

        def fake_updater(obj):
            return obj

        resource = object()
        fake_checker_delayed = get_fake_checker_delayed(seconds=0.3)

        loaded_resource = utils.wait_for(resource, fake_checker_delayed,
                                         fake_updater, 1, 0.2)
        self.assertEqual(loaded_resource, resource)

        loaded_resource = utils.wait_for(resource, fake_checker_delayed,
                                         None, 1, 0.2)
        self.assertEqual(loaded_resource, resource)

        self.assertRaises(exceptions.TimeoutException, utils.wait_for,
                          object(), fake_checker_false, fake_updater, 0.3, 0.1)
