# Copyright 2015: Cisco Systems, Inc.
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
import mock

from rally.plugins.openstack.scenarios.swift import utils
from tests.unit import test

SWIFT_UTILS = "rally.plugins.openstack.scenarios.swift.utils"


@ddt.ddt
class SwiftScenarioTestCase(test.ScenarioTestCase):

    def test__list_containers(self):
        headers_dict = mock.MagicMock()
        containers_list = mock.MagicMock()
        self.clients("swift").get_account.return_value = (headers_dict,
                                                          containers_list)
        scenario = utils.SwiftScenario(context=self.context)

        self.assertEqual((headers_dict, containers_list),
                         scenario._list_containers(fargs="f"))
        kw = {"full_listing": True, "fargs": "f"}
        self.clients("swift").get_account.assert_called_once_with(**kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.list_containers")

    @ddt.data(
        {},
        {"headers": {"X-fake-name": "fake-value"}},
        {"public": False,
         "headers": {"X-fake-name": "fake-value"}},
        {"public": False})
    @ddt.unpack
    def test__create_container(self, public=True, kwargs=None, headers=None):
        if kwargs is None:
            kwargs = {"fakearg": "fake"}
        if headers is None:
            headers = {}
        scenario = utils.SwiftScenario(self.context)
        scenario.generate_random_name = mock.MagicMock()

        container = scenario._create_container(public=public,
                                               headers=headers,
                                               **kwargs)
        self.assertEqual(container,
                         scenario.generate_random_name.return_value)
        kwargs["headers"] = headers
        kwargs["headers"]["X-Container-Read"] = ".r:*,.rlistings"
        self.clients("swift").put_container.assert_called_once_with(
            scenario.generate_random_name.return_value,
            **kwargs)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_container")

    def test__delete_container(self):
        container_name = mock.MagicMock()
        scenario = utils.SwiftScenario(context=self.context)
        scenario._delete_container(container_name, fargs="f")

        kw = {"fargs": "f"}
        self.clients("swift").delete_container.assert_called_once_with(
            container_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_container")

    def test__list_objects(self):
        container_name = mock.MagicMock()
        headers_dict = mock.MagicMock()
        objects_list = mock.MagicMock()
        self.clients("swift").get_container.return_value = (headers_dict,
                                                            objects_list)
        scenario = utils.SwiftScenario(context=self.context)

        self.assertEqual((headers_dict, objects_list),
                         scenario._list_objects(container_name, fargs="f"))
        kw = {"full_listing": True, "fargs": "f"}
        self.clients("swift").get_container.assert_called_once_with(
            container_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.list_objects")

    def test__upload_object(self):
        container_name = mock.MagicMock()
        content = mock.MagicMock()
        etag = mock.MagicMock()
        self.clients("swift").put_object.return_value = etag
        scenario = utils.SwiftScenario(self.context)
        scenario.generate_random_name = mock.MagicMock()

        self.clients("swift").put_object.reset_mock()
        self.assertEqual((etag, scenario.generate_random_name.return_value),
                         scenario._upload_object(container_name, content,
                                                 fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").put_object.assert_called_once_with(
            container_name, scenario.generate_random_name.return_value,
            content, **kw)
        self.assertEqual(1, scenario.generate_random_name.call_count)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.upload_object")

    def test__download_object(self):
        container_name = mock.MagicMock()
        object_name = mock.MagicMock()
        headers_dict = mock.MagicMock()
        content = mock.MagicMock()
        self.clients("swift").get_object.return_value = (headers_dict, content)
        scenario = utils.SwiftScenario(context=self.context)

        self.assertEqual((headers_dict, content),
                         scenario._download_object(container_name, object_name,
                                                   fargs="f"))
        kw = {"fargs": "f"}
        self.clients("swift").get_object.assert_called_once_with(
            container_name, object_name,
            **kw)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.download_object")

    def test__delete_object(self):
        container_name = mock.MagicMock()
        object_name = mock.MagicMock()
        scenario = utils.SwiftScenario(context=self.context)
        scenario._delete_object(container_name, object_name, fargs="f")

        kw = {"fargs": "f"}
        self.clients("swift").delete_object.assert_called_once_with(
            container_name, object_name,
            **kw)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_object")
