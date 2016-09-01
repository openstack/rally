# Copyright 2015 Cisco Systems, Inc.
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

from rally.plugins.openstack.scenarios.swift import objects
from tests.unit import test


@ddt.ddt
class SwiftObjectsTestCase(test.ScenarioTestCase):

    def test_create_container_and_object_then_list_objects(self):
        scenario = objects.CreateContainerAndObjectThenListObjects(
            self.context)
        scenario._create_container = mock.MagicMock(return_value="AA")
        scenario._upload_object = mock.MagicMock()
        scenario._list_objects = mock.MagicMock()

        scenario.run(objects_per_container=5, object_size=100)

        self.assertEqual(1, scenario._create_container.call_count)
        self.assertEqual(5, scenario._upload_object.call_count)
        scenario._list_objects.assert_called_once_with("AA")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_5_objects")

    def test_create_container_and_object_then_delete_all(self):
        scenario = objects.CreateContainerAndObjectThenDeleteAll(self.context)
        scenario._create_container = mock.MagicMock(return_value="BB")
        scenario._upload_object = mock.MagicMock(
            side_effect=[("etaaag", "ooobj_%i" % i) for i in range(3)])
        scenario._delete_object = mock.MagicMock()
        scenario._delete_container = mock.MagicMock()

        scenario.run(objects_per_container=3, object_size=10)

        self.assertEqual(1, scenario._create_container.call_count)
        self.assertEqual(3, scenario._upload_object.call_count)
        scenario._delete_object.assert_has_calls(
            [mock.call("BB", "ooobj_%i" % i,
                       atomic_action=False) for i in range(3)])
        scenario._delete_container.assert_called_once_with("BB")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_3_objects")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_3_objects")

    def test_create_container_and_object_then_download_object(self):
        scenario = objects.CreateContainerAndObjectThenDownloadObject(
            self.context
        )
        scenario._create_container = mock.MagicMock(return_value="CC")
        scenario._upload_object = mock.MagicMock(
            side_effect=[("etaaaag", "obbbj_%i" % i) for i in range(2)])
        scenario._download_object = mock.MagicMock()

        scenario.run(objects_per_container=2, object_size=50)

        self.assertEqual(1, scenario._create_container.call_count)
        self.assertEqual(2, scenario._upload_object.call_count)
        scenario._download_object.assert_has_calls(
            [mock.call("CC", "obbbj_%i" % i,
                       atomic_action=False) for i in range(2)])

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_2_objects")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.download_2_objects")

    @ddt.data(1, 5)
    def test_list_objects_in_containers(self, num_cons):
        con_list = [{"name": "cooon_%s" % i} for i in range(num_cons)]
        scenario = objects.ListObjectsInContainers(self.context)
        scenario._list_containers = mock.MagicMock(return_value=("header",
                                                                 con_list))
        scenario._list_objects = mock.MagicMock()

        scenario.run()
        scenario._list_containers.assert_called_once_with()
        con_calls = [mock.call(container["name"], atomic_action=False)
                     for container in con_list]
        scenario._list_objects.assert_has_calls(con_calls)

        key_suffix = "container"
        if num_cons > 1:
            key_suffix = "%i_containers" % num_cons
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.list_objects_in_%s" % key_suffix)

    @ddt.data([1, 1], [1, 2], [2, 1], [3, 5])
    @ddt.unpack
    def test_list_and_download_objects_in_containers(self, num_cons, num_objs):
        con_list = [{"name": "connn_%s" % i} for i in range(num_cons)]
        obj_list = [{"name": "ooobj_%s" % i} for i in range(num_objs)]
        scenario = objects.ListAndDownloadObjectsInContainers(self.context)
        scenario._list_containers = mock.MagicMock(return_value=("header",
                                                                 con_list))
        scenario._list_objects = mock.MagicMock(return_value=("header",
                                                              obj_list))
        scenario._download_object = mock.MagicMock()

        scenario.run()
        scenario._list_containers.assert_called_once_with()
        con_calls = [mock.call(container["name"], atomic_action=False)
                     for container in con_list]
        scenario._list_objects.assert_has_calls(con_calls)
        obj_calls = []
        for container in con_list:
            for obj in obj_list:
                obj_calls.append(mock.call(container["name"], obj["name"],
                                           atomic_action=False))
        scenario._download_object.assert_has_calls(obj_calls, any_order=True)

        list_key_suffix = "container"
        if num_cons > 1:
            list_key_suffix = "%i_containers" % num_cons
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "swift.list_objects_in_%s" % list_key_suffix)
        download_key_suffix = "object"
        if num_cons * num_objs > 1:
            download_key_suffix = "%i_objects" % (num_cons * num_objs)
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "swift.download_%s" % download_key_suffix)

    def test_functional_create_container_and_object_then_list_objects(self):
        names_list = ["AA", "BB", "CC", "DD"]

        scenario = objects.CreateContainerAndObjectThenListObjects(
            self.context)
        scenario.generate_random_name = mock.MagicMock(side_effect=names_list)
        scenario._list_objects = mock.MagicMock()

        scenario.run(objects_per_container=3, object_size=100)

        scenario._list_objects.assert_called_once_with("AA")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_3_objects")

    def test_functional_create_container_and_object_then_delete_all(self):
        names_list = ["111", "222", "333", "444", "555"]

        scenario = objects.CreateContainerAndObjectThenDeleteAll(self.context)
        scenario.generate_random_name = mock.MagicMock(side_effect=names_list)
        scenario._delete_object = mock.MagicMock()
        scenario._delete_container = mock.MagicMock()

        scenario.run(objects_per_container=4, object_size=240)

        scenario._delete_object.assert_has_calls(
            [mock.call("111", name,
                       atomic_action=False) for name in names_list[1:]])
        scenario._delete_container.assert_called_once_with("111")

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_4_objects")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.delete_4_objects")

    def test_functional_create_container_and_object_then_download_object(self):
        names_list = ["aaa", "bbb", "ccc", "ddd", "eee", "fff"]

        scenario = objects.CreateContainerAndObjectThenDownloadObject(
            self.context)
        scenario.generate_random_name = mock.MagicMock(side_effect=names_list)
        scenario._download_object = mock.MagicMock()

        scenario.run(objects_per_container=5, object_size=750)

        scenario._download_object.assert_has_calls(
            [mock.call("aaa", name,
                       atomic_action=False) for name in names_list[1:]])

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.create_5_objects")
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "swift.download_5_objects")
