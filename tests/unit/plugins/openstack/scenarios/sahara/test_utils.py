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
from oslo_config import cfg
from oslo_utils import uuidutils
from saharaclient.api import base as sahara_base

from rally import consts
from rally import exceptions
from rally.plugins.openstack.scenarios.sahara import utils
from tests.unit import test

CONF = cfg.CONF

SAHARA_UTILS = "rally.plugins.openstack.scenarios.sahara.utils"


class SaharaScenarioTestCase(test.ScenarioTestCase):
    # NOTE(stpierre): the Sahara utils generally do funny stuff with
    # wait_for() calls -- frequently the the is_ready and
    # update_resource arguments are functions defined in the Sahara
    # utils themselves instead of the more standard resource_is() and
    # get_from_manager() calls. As a result, the tests below do more
    # integrated/functional testing of wait_for() calls, and we can't
    # just mock out wait_for and friends the way we usually do.
    patch_benchmark_utils = False

    def setUp(self):
        super(SaharaScenarioTestCase, self).setUp()

        CONF.set_override("sahara_cluster_check_interval", 0, "benchmark",
                          enforce_type=True)
        CONF.set_override("sahara_job_check_interval", 0, "benchmark",
                          enforce_type=True)

    def test_list_node_group_templates(self):
        ngts = []
        self.clients("sahara").node_group_templates.list.return_value = ngts

        scenario = utils.SaharaScenario(self.context)
        return_ngts_list = scenario._list_node_group_templates()

        self.assertEqual(ngts, return_ngts_list)
        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "sahara.list_node_group_templates")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + ".sahara_consts")
    def test_create_node_group_templates(
            self, mock_sahara_consts,
            mock_generate_random_name):

        scenario = utils.SaharaScenario(self.context)
        mock_processes = {
            "test_plugin": {
                "test_version": {
                    "master": ["p1"],
                    "worker": ["p2"]
                }
            }
        }

        mock_sahara_consts.NODE_PROCESSES = mock_processes

        scenario._create_master_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True
        )
        scenario._create_worker_node_group_template(
            flavor_id="test_flavor",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            use_autoconfig=True
        )

        create_calls = [
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p1"],
                use_autoconfig=True),
            mock.call(
                name="random_name",
                plugin_name="test_plugin",
                hadoop_version="test_version",
                flavor_id="test_flavor",
                node_processes=["p2"],
                use_autoconfig=True
            )]
        self.clients("sahara").node_group_templates.create.assert_has_calls(
            create_calls)

        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "sahara.create_master_node_group_template")
        self._test_atomic_action_timer(
            scenario.atomic_actions(),
            "sahara.create_worker_node_group_template")

    def test_delete_node_group_templates(self):
        scenario = utils.SaharaScenario(self.context)
        ng = mock.MagicMock(id=42)

        scenario._delete_node_group_template(ng)

        delete_mock = self.clients("sahara").node_group_templates.delete
        delete_mock.assert_called_once_with(42)

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "sahara.delete_node_group_template")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + ".sahara_consts")
    def test_launch_cluster(self, mock_sahara_consts,
                            mock_generate_random_name):

        self.context.update({
            "tenant": {
                "networks": [
                    {
                        "id": "test_neutron_id",
                        "router_id": "test_router_id"
                    }
                ]
            }
        })

        self.clients("services").values.return_value = [
            consts.Service.NEUTRON
        ]

        scenario = utils.SaharaScenario(context=self.context)

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

        floating_ip_pool_uuid = uuidutils.generate_uuid()
        node_groups = [
            {
                "name": "master-ng",
                "flavor_id": "test_flavor_m",
                "node_processes": ["p1"],
                "floating_ip_pool": floating_ip_pool_uuid,
                "count": 1,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
                "use_autoconfig": True,
            }, {
                "name": "worker-ng",
                "flavor_id": "test_flavor_w",
                "node_processes": ["p2"],
                "floating_ip_pool": floating_ip_pool_uuid,
                "volumes_per_node": 5,
                "volumes_size": 10,
                "count": 42,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
                "use_autoconfig": True,
            }
        ]

        mock_sahara_consts.NODE_PROCESSES = mock_processes
        mock_sahara_consts.REPLICATION_CONFIGS = mock_configs

        self.clients("sahara").clusters.create.return_value.id = (
            "test_cluster_id")

        self.clients("sahara").clusters.get.return_value.status = (
            "active")

        scenario._launch_cluster(
            plugin_name="test_plugin",
            hadoop_version="test_version",
            master_flavor_id="test_flavor_m",
            worker_flavor_id="test_flavor_w",
            image_id="test_image",
            floating_ip_pool=floating_ip_pool_uuid,
            volumes_per_node=5,
            volumes_size=10,
            auto_security_group=True,
            security_groups=["g1", "g2"],
            workers_count=42,
            node_configs={"HDFS": {"local_config": "local_value"}},
            use_autoconfig=True
        )

        self.clients("sahara").clusters.create.assert_called_once_with(
            name="random_name",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            node_groups=node_groups,
            default_image_id="test_image",
            cluster_configs={"HDFS": {"dfs.replication": 3}},
            net_id="test_neutron_id",
            anti_affinity=None,
            use_autoconfig=True
        )

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "sahara.launch_cluster")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + ".sahara_consts")
    def test_launch_cluster_with_proxy(self, mock_sahara_consts,
                                       mock_generate_random_name):

        context = {
            "tenant": {
                "networks": [
                    {
                        "id": "test_neutron_id",
                        "router_id": "test_router_id"
                    }
                ]
            }
        }

        self.clients("services").values.return_value = [
            consts.Service.NEUTRON
        ]

        scenario = utils.SaharaScenario(context=context)

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

        floating_ip_pool_uuid = uuidutils.generate_uuid()
        node_groups = [
            {
                "name": "master-ng",
                "flavor_id": "test_flavor_m",
                "node_processes": ["p1"],
                "floating_ip_pool": floating_ip_pool_uuid,
                "count": 1,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
                "is_proxy_gateway": True,
                "use_autoconfig": True,
            }, {
                "name": "worker-ng",
                "flavor_id": "test_flavor_w",
                "node_processes": ["p2"],
                "volumes_per_node": 5,
                "volumes_size": 10,
                "count": 40,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
                "use_autoconfig": True,
            }, {
                "name": "proxy-ng",
                "flavor_id": "test_flavor_w",
                "node_processes": ["p2"],
                "floating_ip_pool": floating_ip_pool_uuid,
                "volumes_per_node": 5,
                "volumes_size": 10,
                "count": 2,
                "auto_security_group": True,
                "security_groups": ["g1", "g2"],
                "node_configs": {"HDFS": {"local_config": "local_value"}},
                "is_proxy_gateway": True,
                "use_autoconfig": True,
            }
        ]

        mock_sahara_consts.NODE_PROCESSES = mock_processes
        mock_sahara_consts.REPLICATION_CONFIGS = mock_configs

        self.clients("sahara").clusters.create.return_value = mock.MagicMock(
            id="test_cluster_id")

        self.clients("sahara").clusters.get.return_value = mock.MagicMock(
            status="active")

        scenario._launch_cluster(
            plugin_name="test_plugin",
            hadoop_version="test_version",
            master_flavor_id="test_flavor_m",
            worker_flavor_id="test_flavor_w",
            image_id="test_image",
            floating_ip_pool=floating_ip_pool_uuid,
            volumes_per_node=5,
            volumes_size=10,
            auto_security_group=True,
            security_groups=["g1", "g2"],
            workers_count=42,
            node_configs={"HDFS": {"local_config": "local_value"}},
            enable_proxy=True,
            use_autoconfig=True
        )

        self.clients("sahara").clusters.create.assert_called_once_with(
            name="random_name",
            plugin_name="test_plugin",
            hadoop_version="test_version",
            node_groups=node_groups,
            default_image_id="test_image",
            cluster_configs={"HDFS": {"dfs.replication": 3}},
            net_id="test_neutron_id",
            anti_affinity=None,
            use_autoconfig=True
        )

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "sahara.launch_cluster")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="random_name")
    @mock.patch(SAHARA_UTILS + ".sahara_consts")
    def test_launch_cluster_error(self, mock_sahara_consts,
                                  mock_generate_random_name):

        scenario = utils.SaharaScenario(self.context)
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

        mock_sahara_consts.NODE_PROCESSES = mock_processes
        mock_sahara_consts.REPLICATION_CONFIGS = mock_configs

        self.clients("sahara").clusters.create.return_value = mock.MagicMock(
            id="test_cluster_id")

        self.clients("sahara").clusters.get.return_value = mock.MagicMock(
            status="error")

        self.assertRaises(exceptions.GetResourceErrorStatus,
                          scenario._launch_cluster,
                          plugin_name="test_plugin",
                          hadoop_version="test_version",
                          master_flavor_id="test_flavor_m",
                          worker_flavor_id="test_flavor_w",
                          image_id="test_image",
                          floating_ip_pool="test_pool",
                          volumes_per_node=5,
                          volumes_size=10,
                          workers_count=42,
                          node_configs={"HDFS": {"local_config":
                                                 "local_value"}})

    def test_scale_cluster(self):
        scenario = utils.SaharaScenario(self.context)
        cluster = mock.MagicMock(id=42, node_groups=[{
            "name": "random_master",
            "count": 1
        }, {
            "name": "random_worker",
            "count": 41
        }])
        self.clients("sahara").clusters.get.return_value = mock.MagicMock(
            id=42,
            status="active")

        expected_scale_object = {
            "resize_node_groups": [{
                "name": "random_worker",
                "count": 42
            }]
        }

        scenario._scale_cluster(cluster, 1)
        self.clients("sahara").clusters.scale.assert_called_once_with(
            42, expected_scale_object)

    def test_delete_cluster(self):
        scenario = utils.SaharaScenario(self.context)
        cluster = mock.MagicMock(id=42)
        self.clients("sahara").clusters.get.side_effect = [
            cluster, sahara_base.APIException()
        ]

        scenario._delete_cluster(cluster)
        delete_mock = self.clients("sahara").clusters.delete
        delete_mock.assert_called_once_with(42)

        cl_get_expected = mock.call(42)
        self.clients("sahara").clusters.get.assert_has_calls([cl_get_expected,
                                                              cl_get_expected])

        self._test_atomic_action_timer(scenario.atomic_actions(),
                                       "sahara.delete_cluster")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="42")
    def test_create_output_ds(self, mock_generate_random_name):
        self.context.update({
            "sahara": {
                "output_conf": {
                    "output_type": "hdfs",
                    "output_url_prefix": "hdfs://test_out/"
                }
            }
        })

        scenario = utils.SaharaScenario(self.context)
        scenario._create_output_ds()

        self.clients("sahara").data_sources.create.assert_called_once_with(
            name="42",
            description="",
            data_source_type="hdfs",
            url="hdfs://test_out/42"
        )

    @mock.patch(SAHARA_UTILS + ".SaharaScenario.generate_random_name",
                return_value="42")
    def test_create_output_ds_swift(self, mock_generate_random_name):
        self.context.update({
            "sahara": {
                "output_conf": {
                    "output_type": "swift",
                    "output_url_prefix": "swift://test_out/"
                }
            }
        })

        scenario = utils.SaharaScenario(self.context)
        self.assertRaises(exceptions.RallyException,
                          scenario._create_output_ds)

    def test_run_job_execution(self):
        self.clients("sahara").job_executions.get.side_effect = [
            mock.MagicMock(info={"status": "pending"}, id="42"),
            mock.MagicMock(info={"status": "SUCCESS"}, id="42")]

        self.clients("sahara").job_executions.create.return_value = (
            mock.MagicMock(id="42"))

        scenario = utils.SaharaScenario(self.context)
        scenario._run_job_execution(job_id="test_job_id",
                                    cluster_id="test_cluster_id",
                                    input_id="test_input_id",
                                    output_id="test_output_id",
                                    configs={"k": "v"},
                                    job_idx=0)

        self.clients("sahara").job_executions.create.assert_called_once_with(
            job_id="test_job_id",
            cluster_id="test_cluster_id",
            input_id="test_input_id",
            output_id="test_output_id",
            configs={"k": "v"}
        )

        je_get_expected = mock.call("42")
        self.clients("sahara").job_executions.get.assert_has_calls(
            [je_get_expected, je_get_expected]
        )

    def test_run_job_execution_fail(self):
        self.clients("sahara").job_executions.get.side_effect = [
            mock.MagicMock(info={"status": "pending"}, id="42"),
            mock.MagicMock(info={"status": "killed"}, id="42")]

        self.clients("sahara").job_executions.create.return_value = (
            mock.MagicMock(id="42"))

        scenario = utils.SaharaScenario(self.context)
        self.assertRaises(exceptions.RallyException,
                          scenario._run_job_execution,
                          job_id="test_job_id",
                          cluster_id="test_cluster_id",
                          input_id="test_input_id",
                          output_id="test_output_id",
                          configs={"k": "v"},
                          job_idx=0)

        self.clients("sahara").job_executions.create.assert_called_once_with(
            job_id="test_job_id",
            cluster_id="test_cluster_id",
            input_id="test_input_id",
            output_id="test_output_id",
            configs={"k": "v"}
        )
