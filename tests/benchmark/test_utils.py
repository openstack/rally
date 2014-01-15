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

    def test_is_none(self):
        self.assertTrue(utils.is_none(None))
        self.assertFalse(utils.is_none(0))
        self.assertFalse(utils.is_none(""))
        self.assertFalse(utils.is_none("afafa"))

    def test_false(self):
        self.assertFalse(utils.false(None))

    def test_async_clenaup(self):
        cls = mock.MagicMock()
        indicies = {}
        utils.async_cleanup(cls, indicies)
        cls._cleanup_with_clients.assert_called_once_with(indicies)

    def test_infinite_run_args(self):
        args = ("a", "b", "c", "d", 123)
        for i, real_args in enumerate(utils.infinite_run_args(args)):
            self.assertEqual((i,) + args, real_args)
            if i == 10:
                break

    def test_create_openstack_clients(self):
        #TODO(boris-42): Implement this method
        pass

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
