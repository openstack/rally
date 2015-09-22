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

import tempfile

from rally.common import broker
from rally.common import utils as rutils
from rally.plugins.openstack.scenarios.swift import utils as swift_utils


class SwiftObjectMixin(object):
    """Mix-in method for Swift Object Context."""

    def _create_containers(self, context, containers_per_tenant, threads):
        """Create containers and store results in Rally context.

        :param context: dict, Rally context environment
        :param containers_per_tenant: int, number of containers to create
                                      per tenant
        :param threads: int, number of threads to use for broker pattern

        :returns: list of tuples containing (account, container)
        """
        containers = []

        def publish(queue):
            for user, tenant_id in (rutils.iterate_per_tenants(
                    context.get("users", []))):
                context["tenants"][tenant_id]["containers"] = []
                for i in range(containers_per_tenant):
                    args = (user, context["tenants"][tenant_id]["containers"])
                    queue.append(args)

        def consume(cache, args):
            user, tenant_containers = args
            if user["id"] not in cache:
                cache[user["id"]] = swift_utils.SwiftScenario(
                    {"user": user, "task": context.get("task", {})})
            container_name = cache[user["id"]]._create_container()
            tenant_containers.append({"user": user,
                                      "container": container_name,
                                      "objects": []})
            containers.append((user["tenant_id"], container_name))

        broker.run(publish, consume, threads)

        return containers

    def _create_objects(self, context, objects_per_container, object_size,
                        threads):
        """Create objects and store results in Rally context.

        :param context: dict, Rally context environment
        :param objects_per_container: int, number of objects to create
                                      per container
        :param object_size: int, size of created swift objects in byte
        :param threads: int, number of threads to use for broker pattern

        :returns: list of tuples containing (account, container, object)
        """
        objects = []

        with tempfile.TemporaryFile() as dummy_file:
            # set dummy file to specified object size
            dummy_file.truncate(object_size)

            def publish(queue):
                for tenant_id in context["tenants"]:
                    containers = context["tenants"][tenant_id]["containers"]
                    for container in containers:
                        for i in range(objects_per_container):
                            queue.append(container)

            def consume(cache, container):
                user = container["user"]
                if user["id"] not in cache:
                    cache[user["id"]] = swift_utils.SwiftScenario(
                        {"user": user, "task": context.get("task", {})})
                dummy_file.seek(0)
                object_name = cache[user["id"]]._upload_object(
                    container["container"],
                    dummy_file)[1]
                container["objects"].append(object_name)
                objects.append((user["tenant_id"], container["container"],
                                object_name))

            broker.run(publish, consume, threads)

        return objects

    def _delete_containers(self, context, threads):
        """Delete containers created by Swift context and update Rally context.

        :param context: dict, Rally context environment
        :param threads: int, number of threads to use for broker pattern
        """
        def publish(queue):
            for tenant_id in context["tenants"]:
                containers = context["tenants"][tenant_id]["containers"]
                for container in containers[:]:
                    args = container, containers
                    queue.append(args)

        def consume(cache, args):
            container, tenant_containers = args
            user = container["user"]
            if user["id"] not in cache:
                cache[user["id"]] = swift_utils.SwiftScenario(
                    {"user": user, "task": context.get("task", {})})
            cache[user["id"]]._delete_container(container["container"])
            tenant_containers.remove(container)

        broker.run(publish, consume, threads)

    def _delete_objects(self, context, threads):
        """Delete objects created by Swift context and update Rally context.

        :param context: dict, Rally context environment
        :param threads: int, number of threads to use for broker pattern
        """
        def publish(queue):
            for tenant_id in context["tenants"]:
                containers = context["tenants"][tenant_id]["containers"]
                for container in containers:
                    for object_name in container["objects"][:]:
                        args = object_name, container
                        queue.append(args)

        def consume(cache, args):
            object_name, container = args
            user = container["user"]
            if user["id"] not in cache:
                cache[user["id"]] = swift_utils.SwiftScenario(
                    {"user": user, "task": context.get("task", {})})
            cache[user["id"]]._delete_object(container["container"],
                                             object_name)
            container["objects"].remove(object_name)

        broker.run(publish, consume, threads)
