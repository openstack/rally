# Copyright 2016: Servionica LTD.
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

from rally.plugins.openstack.scenarios.watcher import basic
from tests.unit import test


class WatcherTestCase(test.ScenarioTestCase):

    def test_create_audit_template_and_delete(self):
        scenario = basic.CreateAuditTemplateAndDelete(self.context)
        audit_template = mock.Mock()
        scenario._create_audit_template = mock.MagicMock(
            return_value=audit_template)
        scenario._delete_audit_template = mock.MagicMock()
        scenario.run("goal", "strategy")
        scenario._create_audit_template.assert_called_once_with("goal",
                                                                "strategy")
        scenario._delete_audit_template.assert_called_once_with(
            audit_template.uuid)

    def test_list_audit_template(self):
        scenario = basic.ListAuditTemplates(self.context)
        scenario._list_audit_templates = mock.MagicMock()
        scenario.run()
        scenario._list_audit_templates.assert_called_once_with(
            detail=False, goal=None, limit=None, name=None, sort_dir=None,
            sort_key=None, strategy=None)

    def test_create_audit_and_delete(self):
        mock_audit = mock.MagicMock()
        scenario = basic.CreateAuditAndDelete(self.context)
        scenario.context = mock.MagicMock()
        scenario._create_audit = mock.MagicMock(return_value=mock_audit)
        scenario.sleep_between = mock.MagicMock()
        scenario._delete_audit = mock.MagicMock()
        scenario.run()
        scenario._create_audit.assert_called_once_with(mock.ANY)
        scenario._delete_audit.assert_called_once_with(mock_audit)
