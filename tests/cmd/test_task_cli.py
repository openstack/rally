# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013: Mirantis Inc.
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

import uuid

from rally.cmd import task_cli
from rally.openstack.common import test


class TaskCommandsTestCase(test.BaseTestCase):

    def setUp(self):
        super(TaskCommandsTestCase, self).setUp()
        self.task = task_cli.TaskCommands()

    def test_start(self):
        self.task.start('path_to_config.json')

    def test_abort(self):
        self.task.abort(str(uuid.uuid4()))

    def test_status(self):
        self.task.status(str(uuid.uuid4()))

    def test_list(self):
        self.task.list()
