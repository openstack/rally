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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.sahara import utils
from rally.task import types
from rally.task import validation


class SaharaNodeGroupTemplates(utils.SaharaScenario):
    """Benchmark scenarios for Sahara node group templates."""

    @types.convert(flavor={"type": "nova_flavor"})
    @validation.flavor_exists("flavor")
    @validation.required_services(consts.Service.SAHARA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["sahara"]})
    def create_and_list_node_group_templates(self, flavor,
                                             plugin_name="vanilla",
                                             hadoop_version="1.2.1",
                                             use_autoconfig=True):
        """Create and list Sahara Node Group Templates.

        This scenario creates two Node Group Templates with different set of
        node processes. The master Node Group Template contains Hadoop's
        management processes. The worker Node Group Template contains
        Hadoop's worker processes.

        By default the templates are created for the vanilla Hadoop
        provisioning plugin using the version 1.2.1

        After the templates are created the list operation is called.

        :param flavor: Nova flavor that will be for nodes in the
                       created node groups
        :param plugin_name: name of a provisioning plugin
        :param hadoop_version: version of Hadoop distribution supported by
                               the specified plugin.
        :param use_autoconfig: If True, instances of the node group will be
                               automatically configured during cluster
                               creation. If False, the configuration values
                               should be specify manually
        """

        self._create_master_node_group_template(flavor_id=flavor,
                                                plugin_name=plugin_name,
                                                hadoop_version=hadoop_version,
                                                use_autoconfig=use_autoconfig)
        self._create_worker_node_group_template(flavor_id=flavor,
                                                plugin_name=plugin_name,
                                                hadoop_version=hadoop_version,
                                                use_autoconfig=use_autoconfig)
        self._list_node_group_templates()

    @types.convert(flavor={"type": "nova_flavor"})
    @validation.flavor_exists("flavor")
    @validation.required_services(consts.Service.SAHARA)
    @validation.required_openstack(users=True)
    @scenario.configure(context={"cleanup": ["sahara"]})
    def create_delete_node_group_templates(self, flavor,
                                           plugin_name="vanilla",
                                           hadoop_version="1.2.1",
                                           use_autoconfig=True):
        """Create and delete Sahara Node Group Templates.

        This scenario creates and deletes two most common types of
        Node Group Templates.

        By default the templates are created for the vanilla Hadoop
        provisioning plugin using the version 1.2.1

        :param flavor: Nova flavor that will be for nodes in the
                       created node groups
        :param plugin_name: name of a provisioning plugin
        :param hadoop_version: version of Hadoop distribution supported by
                               the specified plugin.
        :param use_autoconfig: If True, instances of the node group will be
                               automatically configured during cluster
                               creation. If False, the configuration values
                               should be specify manually
        """

        master_ngt = self._create_master_node_group_template(
            flavor_id=flavor,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            use_autoconfig=use_autoconfig)

        worker_ngt = self._create_worker_node_group_template(
            flavor_id=flavor,
            plugin_name=plugin_name,
            hadoop_version=hadoop_version,
            use_autoconfig=use_autoconfig)

        self._delete_node_group_template(master_ngt)
        self._delete_node_group_template(worker_ngt)
