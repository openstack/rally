# Copyright 2015: Mirantis Inc.
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
from oslotest import mockpatch

from rally.benchmark.scenarios.murano import utils
from tests.unit import test

BM_UTILS = "rally.benchmark.utils"
MRN_UTILS = "rally.benchmark.scenarios.murano.utils"


class MuranoScenarioTestCase(test.TestCase):

    def setUp(self):
        super(MuranoScenarioTestCase, self).setUp()
        self.res_is = mockpatch.Patch(BM_UTILS + ".resource_is")
        self.get_fm = mockpatch.Patch(BM_UTILS + ".get_from_manager")
        self.wait_for = mockpatch.Patch(MRN_UTILS + ".bench_utils.wait_for")
        self.wait_for_delete = mockpatch.Patch(
            MRN_UTILS + ".bench_utils.wait_for_delete")
        self.useFixture(self.wait_for)
        self.useFixture(self.wait_for_delete)
        self.useFixture(self.res_is)
        self.useFixture(self.get_fm)
        self.gfm = self.get_fm.mock
        self.useFixture(mockpatch.Patch("time.sleep"))

    @mock.patch(MRN_UTILS + ".MuranoScenario.clients")
    def test_list_environments(self, mock_clients):

        mock_clients("murano").environments.list.return_value = []
        scenario = utils.MuranoScenario()
        return_environments_list = scenario._list_environments()
        self.assertEqual([], return_environments_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.list_environments")

    @mock.patch(MRN_UTILS + ".MuranoScenario.clients")
    def test_create_environments(self, mock_clients):
        mock_create = mock.Mock(return_value="foo_env")
        mock_clients("murano").environments.create = mock_create
        scenario = utils.MuranoScenario()
        create_env = scenario._create_environment("env_name")
        self.assertEqual("foo_env", create_env)
        mock_create.assert_called_once_with({"name": "env_name"})
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_environment")

    @mock.patch(MRN_UTILS + ".MuranoScenario.clients")
    def test_delete_environment(self, mock_clients):
        environment = mock.Mock(id="id")
        mock_clients("murano").environments.delete.return_value = "ok"
        scenario = utils.MuranoScenario()
        scenario._delete_environment(environment)
        mock_clients("murano").environments.delete.assert_called_once_with(
            environment.id
        )

        self.wait_for_delete.mock.assert_called_once_with(
            environment,
            update_resource=self.gfm(),
            timeout=180,
            check_interval=2)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.delete_environment")

    @mock.patch(MRN_UTILS + ".MuranoScenario.clients")
    def test_create_session(self, mock_clients):
        mock_clients("murano").sessions.configure.return_value = "sess"
        scenario = utils.MuranoScenario()
        create_sess = scenario._create_session("id")
        self.assertEqual("sess", create_sess)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "murano.create_session")
