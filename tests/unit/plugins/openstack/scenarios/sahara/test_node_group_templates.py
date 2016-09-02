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

BASE = "rally.plugins.openstack.scenarios.sahara.node_group_templates"


class SaharaNodeGroupTemplatesTestCase(test.TestCase):

    def setUp(self):
        super(SaharaNodeGroupTemplatesTestCase, self).setUp()
        self.context = test.get_test_context()

    @mock.patch("%s.CreateAndListNodeGroupTemplates"
                "._list_node_group_templates" % BASE)
    @mock.patch("%s.CreateAndListNodeGroupTemplates"
                "._create_master_node_group_template" % BASE)
    @mock.patch("%s.CreateAndListNodeGroupTemplates"
                "._create_worker_node_group_template" % BASE)
    def test_create_and_list_node_group_templates(self,
                                                  mock_create_worker,
                                                  mock_create_master,
                                                  mock_list_group):
        ngts.CreateAndListNodeGroupTemplates(self.context).run(
            "test_flavor", "test_plugin", "test_version")

        mock_create_master.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock_create_worker.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock_list_group.assert_called_once_with()

    @mock.patch("%s.CreateDeleteNodeGroupTemplates"
                "._delete_node_group_template" % BASE)
    @mock.patch("%s.CreateDeleteNodeGroupTemplates"
                "._create_master_node_group_template" % BASE)
    @mock.patch("%s.CreateDeleteNodeGroupTemplates"
                "._create_worker_node_group_template" % BASE)
    def test_create_delete_node_group_templates(self,
                                                mock_create_worker,
                                                mock_create_master,
                                                mock_delete_group):
        ngts.CreateDeleteNodeGroupTemplates(self.context).run(
            "test_flavor", "test_plugin", "test_version")

        mock_create_master.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)
        mock_create_worker.assert_called_once_with(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True)

        mock_delete_group.assert_has_calls(calls=[
            mock.call(mock_create_master.return_value),
            mock.call(mock_create_worker.return_value)])
