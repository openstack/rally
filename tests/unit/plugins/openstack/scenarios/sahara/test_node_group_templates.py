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

import mock

from rally.plugins.openstack.scenarios.sahara import (node_group_templates
                                                      as ngts)
from tests.unit import test

SAHARA_NGTS = ("rally.plugins.openstack.scenarios.sahara.node_group_templates"
               ".SaharaNodeGroupTemplates")


class SaharaNodeGroupTemplatesTestCase(test.TestCase):

    def setUp(self):
        super(SaharaNodeGroupTemplatesTestCase, self).setUp()
        self.context = test.get_test_context()

    @mock.patch(SAHARA_NGTS + "._list_node_group_templates")
    @mock.patch(SAHARA_NGTS + "._create_master_node_group_template",
                return_value=object())
    @mock.patch(SAHARA_NGTS + "._create_worker_node_group_template",
                return_value=object)
    def test_create_and_list_node_group_templates(
            self,
            mock__create_worker_node_group_template,
            mock__create_master_node_group_template,
            mock__list_node_group_templates):

        ngts_scenario = ngts.SaharaNodeGroupTemplates(self.context)
        ngts_scenario.create_and_list_node_group_templates("test_flavor",
                                                           "test_plugin",
                                                           "test_version")

        mock__create_master_node_group_template.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock__create_worker_node_group_template.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock__list_node_group_templates.assert_called_once_with()

    @mock.patch(SAHARA_NGTS + "._delete_node_group_template")
    @mock.patch(SAHARA_NGTS + "._create_master_node_group_template",
                return_value=mock.MagicMock(id=1))
    @mock.patch(SAHARA_NGTS + "._create_worker_node_group_template",
                return_value=mock.MagicMock(id=2))
    def test_create_delete_node_group_templates(
            self,
            mock__create_worker_node_group_template,
            mock__create_master_node_group_template,
            mock__delete_node_group_template):

        ngts_scenario = ngts.SaharaNodeGroupTemplates(self.context)
        ngts_scenario.create_delete_node_group_templates(
            "test_flavor",
            "test_plugin",
            "test_version")

        mock__create_master_node_group_template.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock__create_worker_node_group_template.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)

        mock__delete_node_group_template.assert_has_calls(calls=[
            mock.call(mock__create_master_node_group_template.return_value),
            mock.call(mock__create_worker_node_group_template.return_value)])
