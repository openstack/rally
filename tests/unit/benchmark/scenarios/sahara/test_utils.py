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
from oslo.config import cfg
from saharaclient.api import base as sahara_base

from rally.benchmark.scenarios.sahara import utils
from rally import exceptions
from tests.unit import test

CONF = cfg.CONF

SAHARA_UTILS = 'rally.benchmark.scenarios.sahara.utils'


class SaharaUtilsTestCase(test.TestCase):

    def setUp(self):
        super(SaharaUtilsTestCase, self).setUp()

        CONF.set_override("cluster_check_interval", 0, "benchmark")
        CONF.set_override("job_check_interval", 0, "benchmark")

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_list_node_group_templates(self, mock_clients):
        ngts = []
        mock_clients("sahara").node_group_templates.list.return_value = ngts

        scenario = utils.SaharaScenario()
        return_ngts_list = scenario._list_node_group_templates()

        self.assertEqual(ngts, return_ngts_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.list_node_group_templates')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_create_node_group_templates(self, mock_clients, mock_random_name):

        scenario = utils.SaharaScenario()
        mock_processes = {
            "test_plugin": {
                "test_version": {
                    "master": ["p1"],
                    "worker": ["p2"]
                }
            }
        }

        scenario.NODE_PROCESSES = mock_processes

        scenario._create_master_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version"
        )
        scenario._create_worker_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version"
        )

        create_calls = [
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p1"]),
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p2"]
            )]
        mock_clients("sahara").node_group_templates.create.assert_has_calls(
            create_calls)

        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            'sahara.create_master_node_group_template')
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            'sahara.create_worker_node_group_template')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_delete_node_group_templates(self, mock_clients):

        scenario = utils.SaharaScenario()
        ng = mock.MagicMock(id=42)

        scenario._delete_node_group_template(ng)

        delete_mock = mock_clients("sahara").node_group_templates.delete
        delete_mock.assert_called_once_with(42)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.delete_node_group_template')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_launch_cluster(self, mock_clients, mock_random_name):

        scenario = utils.SaharaScenario(clients=mock_clients)
        mock_processes = {
            "test_plugin": {
                "test_version": {
                    "master": ["p1"],
                    "worker": ["p2"]
                }
            }
        }

        mock_configs = {
            "test_plugin": {
                "test_version": {
                    "target": "HDFS",
                    "config_name": "dfs.replication"
                }
            }
        }

        node_groups = [
            {
                "name": "master-ng",
                "flavor_id": "test_flavor",
                "node_processes": ["p1"],
                "floating_ip_pool": "test_pool",
                "volumes_per_node": 5,
                "volumes_size": 10,
                "count": 1,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
            }, {
                "name": "worker-ng",
                "flavor_id": "test_flavor",
                "node_processes": ["p2"],
                "floating_ip_pool": "test_pool",
                "volumes_per_node": 5,
                "volumes_size": 10,
                "count": 41,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
            }
        ]

        scenario.NODE_PROCESSES = mock_processes
        scenario.REPLICATION_CONFIGS = mock_configs

        mock_clients("sahara").clusters.create.return_value = mock.MagicMock(
            id="test_cluster_id")

        mock_clients("sahara").clusters.get.return_value = mock.MagicMock(
            status="active")

        scenario._launch_cluster(
            plugin_name="test_plugin",
            hadoop_version="test_version",
            flavor_id="test_flavor",
            image_id="test_image",
            floating_ip_pool="test_pool",
            volumes_per_node=5,
            volumes_size=10,
            auto_security_group=True,
            security_groups=["g1", "g2"],
            node_count=42,
            node_configs={"HDFS": {"local_config": "local_value"}}
        )

        mock_clients("sahara").clusters.create.assert_called_once_with(
            name="random_name",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            node_groups=node_groups,
            default_image_id="test_image",
            cluster_configs={"HDFS": {"dfs.replication": 3}},
            net_id=None
        )

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.launch_cluster')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_launch_cluster_error(self, mock_clients, mock_random_name):

        scenario = utils.SaharaScenario(clients=mock.MagicMock())
        mock_processes = {
            "test_plugin": {
                "test_version": {
                    "master": ["p1"],
                    "worker": ["p2"]
                }
            }
        }

        mock_configs = {
            "test_plugin": {
                "test_version": {
                    "target": "HDFS",
                    "config_name": "dfs.replication"
                }
            }
        }

        scenario.NODE_PROCESSES = mock_processes
        scenario.REPLICATION_CONFIGS = mock_configs

        mock_clients("sahara").clusters.create.return_value = mock.MagicMock(
            id="test_cluster_id")

        mock_clients("sahara").clusters.get.return_value = mock.MagicMock(
            status="error")

        self.assertRaises(exceptions.SaharaClusterFailure,
                          scenario._launch_cluster,
                          plugin_name="test_plugin",
                          hadoop_version="test_version",
                          flavor_id="test_flavor",
                          image_id="test_image",
                          floating_ip_pool="test_pool",
                          volumes_per_node=5,
                          volumes_size=10,
                          node_count=42,
                          node_configs={"HDFS": {"local_config":
                                                 "local_value"}})

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_scale_cluster(self, mock_clients):

        scenario = utils.SaharaScenario()
        cluster = mock.MagicMock(id=42, node_groups=[{
            "name": "random_master",
            "count": 1
        }, {
            "name": "random_worker",
            "count": 41
        }])
        mock_clients("sahara").clusters.get.return_value = mock.MagicMock(
            id=42,
            status="active")

        expected_scale_object = {
            "resize_node_groups": [{
                "name": "random_worker",
                "count": 42
            }]
        }

        scenario._scale_cluster(cluster, 1)
        mock_clients("sahara").clusters.scale.assert_called_once_with(
            42, expected_scale_object)

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_delete_cluster(self, mock_clients):

        scenario = utils.SaharaScenario()
        cluster = mock.MagicMock(id=42)
        mock_clients("sahara").clusters.get.side_effect = [
            cluster, sahara_base.APIException()
        ]

        scenario._delete_cluster(cluster)

        delete_mock = mock_clients("sahara").clusters.delete
        delete_mock.assert_called_once_with(42)

        cl_get_expected = mock.call(42)
        mock_clients("sahara").clusters.get.assert_has_calls([cl_get_expected,
                                                              cl_get_expected])

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       'sahara.delete_cluster')

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="42")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_create_output_ds(self, mock_clients, mock_random_name):

        ctxt = {
            "sahara_output_conf": {
                "output_type": "hdfs",
                "output_url_prefix": "hdfs://test_out/"
            }
        }

        scenario = utils.SaharaScenario(ctxt)
        scenario._create_output_ds()

        mock_clients("sahara").data_sources.create.assert_called_once_with(
            name="42",
            description="",
            data_source_type="hdfs",
            url="hdfs://test_out/42"
        )

    @mock.patch(SAHARA_UTILS + '.SaharaScenario._generate_random_name',
                return_value="42")
    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_create_output_ds_swift(self, mock_clients, mock_random_name):

        ctxt = {
            "sahara_output_conf": {
                "output_type": "swift",
                "output_url_prefix": "swift://test_out/"
            }
        }

        scenario = utils.SaharaScenario(ctxt)
        self.assertRaises(exceptions.RallyException,
                          scenario._create_output_ds)

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_run_job_execution(self, mock_clients):

        mock_clients("sahara").job_executions.get.side_effect = [
            mock.MagicMock(info={"status": "pending"}, id="42"),
            mock.MagicMock(info={"status": "SUCCESS"}, id="42")]

        mock_clients("sahara").job_executions.create.return_value = (
            mock.MagicMock(id="42"))

        scenario = utils.SaharaScenario()
        scenario._run_job_execution(job_id="test_job_id",
                                    cluster_id="test_cluster_id",
                                    input_id="test_input_id",
                                    output_id="test_output_id",
                                    configs={"k": "v"},
                                    job_idx=0)

        mock_clients("sahara").job_executions.create.assert_called_once_with(
            job_id="test_job_id",
            cluster_id="test_cluster_id",
            input_id="test_input_id",
            output_id="test_output_id",
            configs={"k": "v"}
        )

        je_get_expected = mock.call("42")
        mock_clients("sahara").job_executions.get.assert_has_calls(
            [je_get_expected, je_get_expected]
        )

    @mock.patch(SAHARA_UTILS + '.SaharaScenario.clients')
    def test_run_job_execution_fail(self, mock_clients):

        mock_clients("sahara").job_executions.get.side_effect = [
            mock.MagicMock(info={"status": "pending"}, id="42"),
            mock.MagicMock(info={"status": "killed"}, id="42")]

        mock_clients("sahara").job_executions.create.return_value = (
            mock.MagicMock(id="42"))

        scenario = utils.SaharaScenario()
        self.assertRaises(exceptions.RallyException,
                          scenario._run_job_execution,
                          job_id="test_job_id",
                          cluster_id="test_cluster_id",
                          input_id="test_input_id",
                          output_id="test_output_id",
                          configs={"k": "v"},
                          job_idx=0)

        mock_clients("sahara").job_executions.create.assert_called_once_with(
            job_id="test_job_id",
            cluster_id="test_cluster_id",
            input_id="test_input_id",
            output_id="test_output_id",
            configs={"k": "v"}
        )
