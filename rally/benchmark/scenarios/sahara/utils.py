# Copyright 2014: Mirantis Inc.
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

from rally.benchmark.scenarios import base as scenario_base


class SaharaScenario(scenario_base.Scenario):

    RESOURCE_NAME_LENGTH = 20

    # TODO(nkonovalov): Add other provisioning plugins
    NODE_PROCESSES = {
        "vanilla": {
            "1.2.1": {
                "master": ["namenode", "jobtracker"],
                "worker": ["datanode", "tasktracker"]
            },
            "2.3.0": {
                "master": ["namenode", "resourcemanager", "historyserver"],
                "worker": ["datanode", "nodemanager"]
            }
        }
    }

    @scenario_base.atomic_action_timer('sahara.list_node_group_templates')
    def _list_node_group_templates(self):
        """Returns user Node Group Templates list."""

        return self.clients("sahara").node_group_templates.list()

    @scenario_base.atomic_action_timer(
        'sahara.create_master_node_group_template')
    def _create_master_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Creates a master Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
            the plugin
        :return: The created Template
        """

        name = self._generate_random_name(prefix="master-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=self.NODE_PROCESSES[plugin_name][hadoop_version]
            ["master"])

    @scenario_base.atomic_action_timer(
        'sahara.create_worker_node_group_template')
    def _create_worker_node_group_template(self, flavor_id, plugin_name,
                                           hadoop_version):
        """Creates a worker Node Group Template with a random name.

        :param flavor_id: The required argument for the Template
        :param plugin_name: Sahara provisioning plugin name
        :param hadoop_version: The version of Hadoop distribution supported by
            the plugin
        :return: The created Template
        """

        name = self._generate_random_name(prefix="worker-ngt-")

        return self.clients("sahara").node_group_templates.create(
            name=name,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            flavor_id=flavor_id,
            node_processes=self.NODE_PROCESSES[plugin_name][hadoop_version]
            ["worker"])

    @scenario_base.atomic_action_timer('sahara.delete_node_group_template')
    def _delete_node_group_template(self, node_group):
        """Deletes a Node Group Template by id.

        :param node_group: The Node Group Template to be deleted
        :return:
        """

        self.clients("sahara").node_group_templates.delete(node_group.id)
