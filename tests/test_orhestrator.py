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

    def setUp(self):
        super(OrchestratorTestCase, self).setUp()
        self.de = mock.patch('rally.deploy.EngineFactory')
        self.te = mock.patch('rally.benchmark.engine.TestEngine')
        self.de.start()
        self.te.start()

    def tearDonw(self):
        self.de.stop()
        self.te.stop()
        super(OrchestratorTestCase, self).tearDonw()

    def test_start_task(self):
        # TODO(boris-42): Improve these tests, to check that requried mehtods
        #                 are called.
        api.start_task({'deploy': {'name': 'test'}, 'tests': {}})

    def test_abort_task(self):
        self.assertRaises(NotImplementedError, api.abort_task, 'uuid')
