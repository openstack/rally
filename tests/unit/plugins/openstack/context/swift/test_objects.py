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

from rally import exceptions
from rally.plugins.openstack.context.swift import objects
from tests.unit import test


class SwiftObjectGeneratorTestCase(test.TestCase):

    @mock.patch("rally.osclients.Clients")
    def test_setup(self, mock_clients):
        containers_per_tenant = 2
        objects_per_container = 7
        context = test.get_test_context()
        context.update({
            "config": {
                "swift_objects": {
                    "containers_per_tenant": containers_per_tenant,
                    "objects_per_container": objects_per_container,
                    "object_size": 1024,
                    "resource_management_workers": 10
                }
            },
            "tenants": {
                "t1": {"name": "t1_name"},
                "t2": {"name": "t2_name"}
            },
            "users": [
                {"id": "u1", "tenant_id": "t1", "credential": "c1"},
                {"id": "u2", "tenant_id": "t2", "credential": "c2"}
            ]
        })

        objects_ctx = objects.SwiftObjectGenerator(context)
        objects_ctx.setup()

        for tenant_id in context["tenants"]:
            containers = context["tenants"][tenant_id]["containers"]
            self.assertEqual(containers_per_tenant, len(containers))
            for container in containers:
                self.assertEqual(objects_per_container,
                                 len(container["objects"]))

    @mock.patch("rally.osclients.Clients")
    @mock.patch("rally.plugins.openstack.context.swift.utils."
                "swift_utils.SwiftScenario")
    def test_cleanup(self, mock_swift_scenario, mock_clients):
        context = test.get_test_context()
        context.update({
            "config": {
                "swift_objects": {
                    "resource_management_workers": 1
                }
            },
            "tenants": {
                "t1": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {"id": "u1", "tenant_id": "t1",
                                  "credential": "c1"},
                         "container": "c1",
                         "objects": ["o1", "o2", "o3"]}
                    ]
                },
                "t2": {
                    "name": "t2_name",
                    "containers": [
                        {"user": {"id": "u2", "tenant_id": "t2",
                                  "credential": "c2"},
                         "container": "c2",
                         "objects": ["o4", "o5", "o6"]}
                    ]
                }
            }
        })

        objects_ctx = objects.SwiftObjectGenerator(context)
        objects_ctx.cleanup()

        expected_containers = ["c1", "c2"]
        mock_swift_scenario.return_value._delete_container.assert_has_calls(
            [mock.call(con) for con in expected_containers], any_order=True)

        expected_objects = [("c1", "o1"), ("c1", "o2"), ("c1", "o3"),
                            ("c2", "o4"), ("c2", "o5"), ("c2", "o6")]
        mock_swift_scenario.return_value._delete_object.assert_has_calls(
            [mock.call(con, obj) for con, obj in expected_objects],
            any_order=True)

        for tenant_id in context["tenants"]:
            self.assertEqual(0,
                             len(context["tenants"][tenant_id]["containers"]))

    @mock.patch("rally.osclients.Clients")
    def test_setup_failure_clients_put_container(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "config": {
                "swift_objects": {
                    "containers_per_tenant": 2,
                    "object_size": 10,
                    "resource_management_workers": 5
                }
            },
            "tenants": {
                "t1": {"name": "t1_name"},
                "t2": {"name": "t2_name"}
            },
            "users": [
                {"id": "u1", "tenant_id": "t1", "credential": "c1"},
                {"id": "u2", "tenant_id": "t2", "credential": "c2"}
            ]
        })
        mock_swift = mock_clients.return_value.swift.return_value
        mock_swift.put_container.side_effect = [Exception, True,
                                                Exception, Exception]
        objects_ctx = objects.SwiftObjectGenerator(context)
        self.assertRaisesRegexp(exceptions.ContextSetupFailure,
                                "containers, expected 4 but got 1",
                                objects_ctx.setup)

    @mock.patch("rally.osclients.Clients")
    def test_setup_failure_clients_put_object(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "tenants": {
                "t1": {"name": "t1_name"},
                "t2": {"name": "t2_name"}
            },
            "users": [
                {"id": "u1", "tenant_id": "t1", "credential": "c1"},
                {"id": "u2", "tenant_id": "t2", "credential": "c2"}
            ]
        })
        mock_swift = mock_clients.return_value.swift.return_value
        mock_swift.put_object.side_effect = [Exception, True]
        objects_ctx = objects.SwiftObjectGenerator(context)
        self.assertRaisesRegexp(exceptions.ContextSetupFailure,
                                "objects, expected 2 but got 1",
                                objects_ctx.setup)

    @mock.patch("rally.osclients.Clients")
    def test_cleanup_failure_clients_delete_container(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "tenants": {
                "t1": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {"id": "u1", "tenant_id": "t1",
                                  "credential": "c1"},
                         "container": "coooon",
                         "objects": []}] * 3
                }
            }
        })
        mock_swift = mock_clients.return_value.swift.return_value
        mock_swift.delete_container.side_effect = [True, True, Exception]
        objects_ctx = objects.SwiftObjectGenerator(context)
        objects_ctx.cleanup()
        self.assertEqual(1, len(context["tenants"]["t1"]["containers"]))

    @mock.patch("rally.osclients.Clients")
    def test_cleanup_failure_clients_delete_object(self, mock_clients):
        context = test.get_test_context()
        context.update({
            "tenants": {
                "t1": {
                    "name": "t1_name",
                    "containers": [
                        {"user": {"id": "u1", "tenant_id": "t1",
                                  "credential": "c1"},
                         "container": "c1",
                         "objects": ["oooo"] * 3}
                    ]
                }
            }
        })
        mock_swift = mock_clients.return_value.swift.return_value
        mock_swift.delete_object.side_effect = [True, Exception, True]
        objects_ctx = objects.SwiftObjectGenerator(context)
        objects_ctx._delete_containers = mock.MagicMock()
        objects_ctx.cleanup()
        self.assertEqual(
            1, sum([len(container["objects"])
                    for container in context["tenants"]["t1"]["containers"]]))
