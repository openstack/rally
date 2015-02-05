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

from rally.benchmark.scenarios.sahara import jobs
from tests.unit import test


CONF = cfg.CONF

SAHARA_JOB = "rally.benchmark.scenarios.sahara.jobs.SaharaJob"
SAHARA_UTILS = "rally.benchmark.scenarios.sahara.utils"


class SaharaJobTestCase(test.TestCase):

    def setUp(self):
        super(SaharaJobTestCase, self).setUp()

        CONF.set_override("cluster_check_interval", 0, "benchmark")
        CONF.set_override("job_check_interval", 0, "benchmark")

    @mock.patch(SAHARA_UTILS + ".SaharaScenario._generate_random_name",
                return_value="job_42")
    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_UTILS + ".SaharaScenario.clients")
    def test_create_launch_job_java(self, mock_osclients, mock_run_execution,
                                    mock_random_name):

        mock_sahara = mock_osclients("sahara")
        mock_sahara.jobs.create.return_value = mock.MagicMock(id="42")

        jobs_scenario = jobs.SaharaJob()

        jobs_scenario.context = {
            "tenant": {
                "sahara_image": "test_image",
                "sahara_mains": ["main_42"],
                "sahara_libs": ["lib_42"],
                "sahara_cluster": "cl_42",
                "sahara_input": "in_42"
            }
        }
        jobs_scenario.create_launch_job(
            job_type="java",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )
        mock_sahara.jobs.create.assert_called_once_with(
            name=mock_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock_run_execution.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id=None,
            output_id=None,
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch(SAHARA_UTILS + ".SaharaScenario._generate_random_name",
                return_value="job_42")
    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_JOB + "._create_output_ds",
                return_value=mock.MagicMock(id="out_42"))
    @mock.patch(SAHARA_UTILS + ".SaharaScenario.clients")
    def test_create_launch_job_pig(self, mock_osclients, mock_create_ds,
                                   mock_run_execution, mock_random_name):

        mock_sahara = mock_osclients("sahara")
        mock_sahara.jobs.create.return_value = mock.MagicMock(id="42")

        jobs_scenario = jobs.SaharaJob()

        jobs_scenario.context = {
            "tenant": {
                "sahara_image": "test_image",
                "sahara_mains": ["main_42"],
                "sahara_libs": ["lib_42"],
                "sahara_cluster": "cl_42",
                "sahara_input": "in_42"
            }
        }
        jobs_scenario.create_launch_job(
            job_type="pig",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )
        mock_sahara.jobs.create.assert_called_once_with(
            name=mock_random_name.return_value,
            type="pig",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock_run_execution.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id="in_42",
            output_id="out_42",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch(SAHARA_UTILS + ".SaharaScenario._generate_random_name",
                return_value="job_42")
    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_UTILS + ".SaharaScenario.clients")
    def test_create_launch_job_sequence(self, mock_osclients,
                                        mock_run_execution, mock_random_name):

        mock_sahara = mock_osclients("sahara")
        mock_sahara.jobs.create.return_value = mock.MagicMock(id="42")

        jobs_scenario = jobs.SaharaJob()

        jobs_scenario.context = {
            "tenant": {
                "sahara_image": "test_image",
                "sahara_mains": ["main_42"],
                "sahara_libs": ["lib_42"],
                "sahara_cluster": "cl_42",
                "sahara_input": "in_42"
            }
        }
        jobs_scenario.create_launch_job_sequence(
            jobs=[
                {
                    "job_type": "java",
                    "configs": {"conf_key": "conf_val"}
                }, {
                    "job_type": "java",
                    "configs": {"conf_key2": "conf_val2"}
                }])

        jobs_create_call = mock.call(
            name=mock_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"])

        mock_sahara.jobs.create.assert_has_calls([jobs_create_call,
                                                  jobs_create_call])

        mock_run_execution.assert_has_calls([
            mock.call(
                job_id="42",
                cluster_id="cl_42",
                input_id=None,
                output_id=None,
                configs={"conf_key": "conf_val"},
                job_idx=0),
            mock.call(
                job_id="42",
                cluster_id="cl_42",
                input_id=None,
                output_id=None,
                configs={"conf_key2": "conf_val2"},
                job_idx=1)]
        )

    @mock.patch(SAHARA_UTILS + ".SaharaScenario._generate_random_name",
                return_value="job_42")
    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_JOB + "._scale_cluster")
    @mock.patch(SAHARA_UTILS + ".SaharaScenario.clients")
    def test_create_launch_job_sequence_with_scaling(self, mock_osclients,
                                                     mock_scale,
                                                     mock_run_execution,
                                                     mock_random_name):

        mock_sahara = mock_osclients("sahara")
        mock_sahara.jobs.create.return_value = mock.MagicMock(id="42")
        mock_sahara.clusters.get.return_value = mock.MagicMock(
            id="cl_42",
            status="active")

        jobs_scenario = jobs.SaharaJob()

        jobs_scenario.context = {
            "tenant": {
                "sahara_image": "test_image",
                "sahara_mains": ["main_42"],
                "sahara_libs": ["lib_42"],
                "sahara_cluster": "cl_42",
                "sahara_input": "in_42"
            }
        }
        jobs_scenario.create_launch_job_sequence_with_scaling(
            jobs=[
                {
                    "job_type": "java",
                    "configs": {"conf_key": "conf_val"}
                }, {
                    "job_type": "java",
                    "configs": {"conf_key2": "conf_val2"}
                }],
            deltas=[1, -1])

        jobs_create_call = mock.call(
            name=mock_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"])

        mock_sahara.jobs.create.assert_has_calls([jobs_create_call,
                                                  jobs_create_call])

        je_0 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None, configs={"conf_key": "conf_val"},
                         job_idx=0)
        je_1 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None,
                         configs={"conf_key2": "conf_val2"}, job_idx=1)
        mock_run_execution.assert_has_calls([je_0, je_1, je_0, je_1, je_0,
                                             je_1])
