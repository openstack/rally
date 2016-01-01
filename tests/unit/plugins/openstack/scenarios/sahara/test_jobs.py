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

from rally.plugins.openstack.scenarios.sahara import jobs
from tests.unit import test

CONF = cfg.CONF

SAHARA_JOB = "rally.plugins.openstack.scenarios.sahara.jobs.SaharaJob"
SAHARA_UTILS = "rally.plugins.openstack.scenarios.sahara.utils"


class SaharaJobTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaJobTestCase, self).setUp()

        self.context = test.get_test_context()
        CONF.set_override("sahara_cluster_check_interval", 0, "benchmark",
                          enforce_type=True)
        CONF.set_override("sahara_job_check_interval", 0, "benchmark",
                          enforce_type=True)

    @mock.patch(SAHARA_JOB + "._run_job_execution")
    def test_create_launch_job_java(self, mock__run_job_execution):
        self.clients("sahara").jobs.create.return_value = mock.MagicMock(
            id="42")

        self.context.update({
            "tenant": {
                "sahara": {
                    "image": "test_image",
                    "mains": ["main_42"],
                    "libs": ["lib_42"],
                    "cluster": "cl_42",
                    "input": "in_42"
                }
            }
        })
        jobs_scenario = jobs.SaharaJob(self.context)
        jobs_scenario.generate_random_name = mock.Mock(return_value="job_42")

        jobs_scenario.create_launch_job(
            job_type="java",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )
        self.clients("sahara").jobs.create.assert_called_once_with(
            name=jobs_scenario.generate_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock__run_job_execution.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id=None,
            output_id=None,
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_JOB + "._create_output_ds",
                return_value=mock.MagicMock(id="out_42"))
    def test_create_launch_job_pig(self, mock__create_output_ds,
                                   mock__run_job_execution):
        self.clients("sahara").jobs.create.return_value = mock.MagicMock(
            id="42")

        self.context.update({
            "tenant": {
                "sahara": {
                    "image": "test_image",
                    "mains": ["main_42"],
                    "libs": ["lib_42"],
                    "cluster": "cl_42",
                    "input": "in_42"
                }
            }
        })
        jobs_scenario = jobs.SaharaJob(self.context)
        jobs_scenario.generate_random_name = mock.Mock(return_value="job_42")

        jobs_scenario.create_launch_job(
            job_type="pig",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )
        self.clients("sahara").jobs.create.assert_called_once_with(
            name=jobs_scenario.generate_random_name.return_value,
            type="pig",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock__run_job_execution.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id="in_42",
            output_id="out_42",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch(SAHARA_JOB + "._run_job_execution")
    def test_create_launch_job_sequence(self, mock__run_job_execution):
        self.clients("sahara").jobs.create.return_value = mock.MagicMock(
            id="42")

        self.context.update({
            "tenant": {
                "sahara": {
                    "image": "test_image",
                    "mains": ["main_42"],
                    "libs": ["lib_42"],
                    "cluster": "cl_42",
                    "input": "in_42"
                }
            }
        })
        jobs_scenario = jobs.SaharaJob(self.context)
        jobs_scenario.generate_random_name = mock.Mock(return_value="job_42")

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
            name=jobs_scenario.generate_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"])

        self.clients("sahara").jobs.create.assert_has_calls([jobs_create_call,
                                                             jobs_create_call])

        mock__run_job_execution.assert_has_calls([
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

    @mock.patch(SAHARA_JOB + "._run_job_execution")
    @mock.patch(SAHARA_JOB + "._scale_cluster")
    def test_create_launch_job_sequence_with_scaling(self,
                                                     mock__scale_cluster,
                                                     mock__run_job_execution):
        self.clients("sahara").jobs.create.return_value = mock.MagicMock(
            id="42")
        self.clients("sahara").clusters.get.return_value = mock.MagicMock(
            id="cl_42", status="active")

        self.context.update({
            "tenant": {
                "sahara": {
                    "image": "test_image",
                    "mains": ["main_42"],
                    "libs": ["lib_42"],
                    "cluster": "cl_42",
                    "input": "in_42"
                }
            }
        })
        jobs_scenario = jobs.SaharaJob(self.context)
        jobs_scenario.generate_random_name = mock.Mock(return_value="job_42")

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
            name=jobs_scenario.generate_random_name.return_value,
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"])

        self.clients("sahara").jobs.create.assert_has_calls([jobs_create_call,
                                                             jobs_create_call])

        je_0 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None, configs={"conf_key": "conf_val"},
                         job_idx=0)
        je_1 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None,
                         configs={"conf_key2": "conf_val2"}, job_idx=1)
        mock__run_job_execution.assert_has_calls(
            [je_0, je_1, je_0, je_1, je_0, je_1])
