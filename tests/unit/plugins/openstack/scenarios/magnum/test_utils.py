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

from rally.plugins.openstack.scenarios.magnum import utils
from tests.unit import test

CONF = utils.CONF


class MagnumScenarioTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(MagnumScenarioTestCase, self).setUp()
        self.cluster_template = mock.Mock()
        self.cluster = mock.Mock()
        self.scenario = utils.MagnumScenario(self.context)

    def test_list_cluster_templates(self):
        fake_list = [self.cluster_template]

        self.clients("magnum").cluster_templates.list.return_value = fake_list
        return_ct_list = self.scenario._list_cluster_templates()
        self.assertEqual(fake_list, return_ct_list)

        self.clients("magnum").cluster_templates.list.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "magnum.list_cluster_templates")

    def test_create_cluster_template(self):
        self.scenario.generate_random_name = mock.Mock(
            return_value="generated_name")
        fake_ct = self.cluster_template
        self.clients("magnum").cluster_templates.create.return_value = fake_ct

        return_cluster_template = self.scenario._create_cluster_template(
            image="test_image",
            keypair="test_key",
            external_network="public",
            dns_nameserver="8.8.8.8",
            flavor="m1.large",
            docker_volume_size=50,
            network_driver="docker",
            coe="swarm")

        self.assertEqual(fake_ct, return_cluster_template)
        _, kwargs = self.clients("magnum").cluster_templates.create.call_args
        self.assertEqual("generated_name", kwargs["name"])

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "magnum.create_cluster_template")

    def test_list_clusters(self):
        return_clusters_list = self.scenario._list_clusters(limit="foo1")
        client = self.clients("magnum")
        client.clusters.list.assert_called_once_with(limit="foo1")
        self.assertEqual(client.clusters.list.return_value,
                         return_clusters_list)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.list_clusters")

    def test_create_cluster(self):
        self.scenario.generate_random_name = mock.Mock(
            return_value="generated_name")
        self.clients("magnum").clusters.create.return_value = self.cluster
        return_cluster = self.scenario._create_cluster(
            cluster_template="generated_uuid", node_count=2)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.cluster,
            ready_statuses=["CREATE_COMPLETE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.benchmark.
            magnum_cluster_create_poll_interval,
            timeout=CONF.benchmark.magnum_cluster_create_timeout,
            id_attr="uuid")
        _, kwargs = self.clients("magnum").clusters.create.call_args
        self.assertEqual("generated_name", kwargs["name"])
        self.assertEqual("generated_uuid", kwargs["cluster_template_id"])
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(
            self.mock_wait_for_status.mock.return_value, return_cluster)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.create_cluster")
