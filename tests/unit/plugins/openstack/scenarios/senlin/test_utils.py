# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from oslo_config import cfg

from rally import exceptions
from rally.plugins.openstack.scenarios.senlin import utils
from tests.unit import test

SENLIN_UTILS = "rally.plugins.openstack.scenarios.senlin.utils."
CONF = cfg.CONF


class SenlinScenarioTestCase(test.ScenarioTestCase):

    def test_list_cluster(self):
        fake_cluster_list = ["cluster1", "cluster2"]
        self.admin_clients("senlin").clusters.return_value = fake_cluster_list
        scenario = utils.SenlinScenario(self.context)
        result = scenario._list_clusters()

        self.assertEqual(list(fake_cluster_list), result)
        self.admin_clients("senlin").clusters.assert_called_once_with()

    def test_list_cluster_with_queries(self):
        fake_cluster_list = ["cluster1", "cluster2"]
        self.admin_clients("senlin").clusters.return_value = fake_cluster_list
        scenario = utils.SenlinScenario(self.context)
        result = scenario._list_clusters(status="ACTIVE")

        self.assertEqual(list(fake_cluster_list), result)
        self.admin_clients("senlin").clusters.assert_called_once_with(
            status="ACTIVE")

    @mock.patch(SENLIN_UTILS + "SenlinScenario.generate_random_name",
                return_value="test_cluster")
    def test_create_cluster(self, mock_generate_random_name):
        fake_cluster = mock.Mock(id="fake_cluster_id")
        res_cluster = mock.Mock()
        self.admin_clients("senlin").create_cluster.return_value = fake_cluster
        self.mock_wait_for_status.mock.return_value = res_cluster
        scenario = utils.SenlinScenario(self.context)
        result = scenario._create_cluster("fake_profile_id",
                                          desired_capacity=1,
                                          min_size=0,
                                          max_size=3,
                                          metadata={"k1": "v1"},
                                          timeout=60)

        self.assertEqual(res_cluster, result)
        self.admin_clients("senlin").create_cluster.assert_called_once_with(
            profile_id="fake_profile_id", name="test_cluster",
            desired_capacity=1, min_size=0, max_size=3, metadata={"k1": "v1"},
            timeout=60)
        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_cluster, ready_statuses=["ACTIVE"],
            failure_statuses=["ERROR"],
            update_resource=scenario._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)
        mock_generate_random_name.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "senlin.create_cluster")

    def test_get_cluster(self):
        fake_cluster = mock.Mock(id="fake_cluster_id")
        scenario = utils.SenlinScenario(context=self.context)
        scenario._get_cluster(fake_cluster)

        self.admin_clients("senlin").get_cluster.assert_called_once_with(
            "fake_cluster_id")

    def test_get_cluster_notfound(self):
        fake_cluster = mock.Mock(id="fake_cluster_id")
        ex = Exception()
        ex.code = 404
        self.admin_clients("senlin").get_cluster.side_effect = ex
        scenario = utils.SenlinScenario(context=self.context)

        self.assertRaises(exceptions.GetResourceNotFound,
                          scenario._get_cluster,
                          fake_cluster)
        self.admin_clients("senlin").get_cluster.assert_called_once_with(
            "fake_cluster_id")

    def test_get_cluster_failed(self):
        fake_cluster = mock.Mock(id="fake_cluster_id")
        ex = Exception()
        ex.code = 500
        self.admin_clients("senlin").get_cluster.side_effect = ex
        scenario = utils.SenlinScenario(context=self.context)

        self.assertRaises(exceptions.GetResourceFailure,
                          scenario._get_cluster,
                          fake_cluster)
        self.admin_clients("senlin").get_cluster.assert_called_once_with(
            "fake_cluster_id")

    def test_delete_cluster(self):
        fake_cluster = mock.Mock()
        scenario = utils.SenlinScenario(context=self.context)
        scenario._delete_cluster(fake_cluster)

        self.admin_clients("senlin").delete_cluster.assert_called_once_with(
            fake_cluster)
        self.mock_wait_for_status.mock.assert_called_once_with(
            fake_cluster, ready_statuses=["DELETED"],
            failure_statuses=["ERROR"], check_deletion=True,
            update_resource=scenario._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "senlin.delete_cluster")

    @mock.patch(SENLIN_UTILS + "SenlinScenario.generate_random_name",
                return_value="test_profile")
    def test_create_profile(self, mock_generate_random_name):
        test_spec = {
            "version": "1.0",
            "type": "test_type",
            "properties": {
                "key1": "value1"
            }
        }
        scenario = utils.SenlinScenario(self.context)
        result = scenario._create_profile(test_spec, metadata={"k2": "v2"})

        self.assertEqual(
            self.clients("senlin").create_profile.return_value, result)
        self.clients("senlin").create_profile.assert_called_once_with(
            spec=test_spec, name="test_profile", metadata={"k2": "v2"})
        mock_generate_random_name.assert_called_once_with()
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "senlin.create_profile")

    def test_delete_profile(self):
        fake_profile = mock.Mock()
        scenario = utils.SenlinScenario(context=self.context)
        scenario._delete_profile(fake_profile)

        self.clients("senlin").delete_profile.assert_called_once_with(
            fake_profile)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "senlin.delete_profile")
