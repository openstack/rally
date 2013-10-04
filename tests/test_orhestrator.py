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

""" Test for orchestrator. """

import mock

from rally.orchestrator import api
from rally import test


class OrchestratorTestCase(test.NoDBTestCase):

    def test_start_task(self):
        config = {'deploy': {'name': 'test'}, 'tests': {}}

        with mock.patch("rally.orchestrator.api.task"):
            with mock.patch("rally.orchestrator.api.deploy"):
                with mock.patch("rally.orchestrator.api.engine"):
                    # NOTE(boris-42) Improve this test case.
                    api.start_task(config)

    def test_abort_task(self):
        self.assertRaises(NotImplementedError, api.abort_task, 'uuid')
