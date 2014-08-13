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

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios.sahara import utils
from rally.benchmark import types
from rally.benchmark import validation
from rally import consts


class SaharaNodeGroupTemplates(utils.SaharaScenario):

    @types.set(flavor=types.FlavorResourceType)
    @validation.add(validation.flavor_exists('flavor'))
    @base.scenario(context={"cleanup": ["sahara"]})
    @validation.required_services(consts.Service.SAHARA)
    def create_and_list_node_group_templates(self, flavor,
                                             plugin_name="vanilla",
                                             hadoop_version="1.2.1"):
        """Test the sahara Node Group Templates create and list commands.

        This scenario creates two Node Group Templates with different set of
        node processes. The master Node Group Template contains Hadoop's
        management processes. The worker Node Group Template contains
        Haddop's worker processes.

        By default the templates are created for the vanilla Hadoop
        provisioning plugin using the version 1.2.1

        After the templates are created the list operation is called.

        :param flavor: The Nova flavor that will be for nodes in the
        created node groups
        :param plugin_name: The name of a provisioning plugin
        :param hadoop_version: The version of Hadoop distribution supported by
        the specified plugin.
        """

        self._create_master_node_group_template(flavor_id=flavor,
                                                plugin_name=plugin_name,
                                                hadoop_version=hadoop_version)
        self._create_worker_node_group_template(flavor_id=flavor,
                                                plugin_name=plugin_name,
                                                hadoop_version=hadoop_version)
        self._list_node_group_templates()

    @types.set(flavor=types.FlavorResourceType)
    @validation.add(validation.flavor_exists('flavor'))
    @base.scenario(context={"cleanup": ["sahara"]})
    @validation.required_services(consts.Service.SAHARA)
    def create_delete_node_group_templates(self, flavor,
                                           plugin_name="vanilla",
                                           hadoop_version="1.2.1"):
        """Test create and delete commands.

        This scenario creates and deletes two most common types of
        Node Group Templates.

        By default the templates are created for the vanilla Hadoop
        provisioning plugin using the version 1.2.1

        :param flavor: The Nova flavor that will be for nodes in the
        created node groups
        :param plugin_name: The name of a provisioning plugin
        :param hadoop_version: The version of Hadoop distribution supported by
        the specified plugin.
        """

        master_ngt = self._create_master_node_group_template(
            flavor_id=flavor,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version)

        worker_ngt = self._create_worker_node_group_template(
            flavor_id=flavor,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version)

        self._delete_node_group_template(master_ngt)
        self._delete_node_group_template(worker_ngt)
