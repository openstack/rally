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

import mock

from rally.plugins.openstack.context.swift import utils
from tests.unit import test


class SwiftObjectMixinTestCase(test.TestCase):

    @mock.patch("rally.osclients.Clients")
    def test__create_containers(self, mock_clients):
        tenants = 2
        containers_per_tenant = 2
        context = test.get_test_context()
        context.update({
            "tenants": {
                "1001": {"name": "t1_name"},
                "1002": {"name": "t2_name"}
            },
            "users": [
                {"id": "u1", "tenant_id": "1001", "credential": "c1"},
                {"id": "u2", "tenant_id": "1002", "credential": "c2"}
            ]
        })

        mixin = utils.SwiftObjectMixin()
        containers = mixin._create_containers(context, containers_per_tenant,
                                              15)

        self.assertEqual(tenants * containers_per_tenant, len(containers))
        for index, container in enumerate(sorted(containers)):
            offset = int(index / containers_per_tenant) + 1
            self.assertEqual(str(1000 + offset), container[0])

        for index, tenant_id in enumerate(sorted(context["tenants"]), start=1):
            containers = context["tenants"][tenant_id]["containers"]
            self.assertEqual(containers_per_tenant, len(containers))
            for container in containers:
                self.assertEqual("u%d" % index, container["user"]["id"])
                self.assertEqual("c%d" % index,
                                 container["user"]["credential"])
                self.assertEqual(0, len(container["objects"]))

    @mock.patch("rally.osclients.Clients")
    def test__create_objects(self, mock_clients):
        tenants = 2
        containers_per_tenant = 1
        objects_per_container = 5
        context = test.get_test_context()
        context.update({
            "tenants": {
                "1001": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {
                            "id": "u1", "tenant_id": "1001",
                            "credential": "c0"},
                         "container": "c1",
                         "objects": []}
                    ]
                },
                "1002": {
                    "name": "t2_name",
                    "containers": [
                        {"user": {
                            "id": "u2", "tenant_id": "1002",
                            "credential": "c2"},
                         "container": "c2",
                         "objects": []}
                    ]
                }
            }
        })

        mixin = utils.SwiftObjectMixin()
        objects_list = mixin._create_objects(context, objects_per_container,
                                             1024, 25)

        self.assertEqual(
            tenants * containers_per_tenant * objects_per_container,
            len(objects_list))
        chunk = containers_per_tenant * objects_per_container
        for index, obj in enumerate(sorted(objects_list)):
            offset = int(index / chunk) + 1
            self.assertEqual(str(1000 + offset), obj[0])
            self.assertEqual("c%d" % offset, obj[1])

        for tenant_id in context["tenants"]:
            for container in context["tenants"][tenant_id]["containers"]:
                self.assertEqual(objects_per_container,
                                 len(container["objects"]))

    @mock.patch("rally.osclients.Clients")
    def test__delete_containers(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "tenants": {
                "1001": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {
                            "id": "u1", "tenant_id": "1001",
                            "credential": "c1"},
                         "container": "c1",
                         "objects": []}
                    ]
                },
                "1002": {
                    "name": "t2_name",
                    "containers": [
                        {"user": {
                            "id": "u2", "tenant_id": "1002",
                            "credential": "c2"},
                         "container": "c2",
                         "objects": []}
                    ]
                }
            }
        })

        mixin = utils.SwiftObjectMixin()
        mixin._delete_containers(context, 1)

        mock_swift = mock_clients.return_value.swift.return_value
        expected_containers = ["c1", "c2"]
        mock_swift.delete_container.assert_has_calls(
            [mock.call(con) for con in expected_containers], any_order=True)

        for tenant_id in context["tenants"]:
            self.assertEqual(0,
                             len(context["tenants"][tenant_id]["containers"]))

    @mock.patch("rally.osclients.Clients")
    def test__delete_objects(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "tenants": {
                "1001": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {
                            "id": "u1", "tenant_id": "1001",
                            "credential": "c1"},
                         "container": "c1",
                         "objects": ["o1", "o2", "o3"]}
                    ]
                },
                "1002": {
                    "name": "t2_name",
                    "containers": [
                        {"user": {
                            "id": "u2", "tenant_id": "1002",
                            "credential": "c2"},
                         "container": "c2",
                         "objects": ["o4", "o5", "o6"]}
                    ]
                }
            }
        })

        mixin = utils.SwiftObjectMixin()
        mixin._delete_objects(context, 1)

        mock_swift = mock_clients.return_value.swift.return_value
        expected_objects = [("c1", "o1"), ("c1", "o2"), ("c1", "o3"),
                            ("c2", "o4"), ("c2", "o5"), ("c2", "o6")]
        mock_swift.delete_object.assert_has_calls(
            [mock.call(con, obj) for con, obj in expected_objects],
            any_order=True)

        for tenant_id in context["tenants"]:
            for container in context["tenants"][tenant_id]["containers"]:
                self.assertEqual(0, len(container["objects"]))
