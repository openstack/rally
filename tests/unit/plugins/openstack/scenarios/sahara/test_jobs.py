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

BASE = "rally.plugins.openstack.scenarios.sahara.jobs"


class SaharaJobTestCase(test.ScenarioTestCase):

    def setUp(self):
        super(SaharaJobTestCase, self).setUp()

        self.context = test.get_test_context()
        CONF.set_override("sahara_cluster_check_interval", 0, "benchmark",
                          enforce_type=True)
        CONF.set_override("sahara_job_check_interval", 0, "benchmark",
                          enforce_type=True)

    @mock.patch("%s.CreateLaunchJob._run_job_execution" % BASE)
    def test_create_launch_job_java(self, mock_run_job):
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
        scenario = jobs.CreateLaunchJob(self.context)
        scenario.generate_random_name = mock.Mock(
            return_value="job_42")

        scenario.run(job_type="java",
                     configs={"conf_key": "conf_val"},
                     job_idx=0)
        self.clients("sahara").jobs.create.assert_called_once_with(
            name="job_42",
            type="java",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock_run_job.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id=None,
            output_id=None,
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch("%s.CreateLaunchJob._run_job_execution" % BASE)
    @mock.patch("%s.CreateLaunchJob._create_output_ds" % BASE,
                return_value=mock.MagicMock(id="out_42"))
    def test_create_launch_job_pig(self,
                                   mock_create_output,
                                   mock_run_job):
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
        scenario = jobs.CreateLaunchJob(self.context)
        scenario.generate_random_name = mock.Mock(return_value="job_42")

        scenario.run(job_type="pig",
                     configs={"conf_key": "conf_val"},
                     job_idx=0)
        self.clients("sahara").jobs.create.assert_called_once_with(
            name="job_42",
            type="pig",
            description="",
            mains=["main_42"],
            libs=["lib_42"]
        )

        mock_run_job.assert_called_once_with(
            job_id="42",
            cluster_id="cl_42",
            input_id="in_42",
            output_id="out_42",
            configs={"conf_key": "conf_val"},
            job_idx=0
        )

    @mock.patch("%s.CreateLaunchJob._run_job_execution" % BASE)
    @mock.patch("%s.CreateLaunchJob.generate_random_name" % BASE,
                return_value="job_42")
    def test_create_launch_job_sequence(self,
                                        mock__random_name,
                                        mock_run_job):
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
        scenario = jobs.CreateLaunchJobSequence(self.context)

        scenario.run(
            jobs=[
                {
                    "job_type": "java",
                    "configs": {"conf_key": "conf_val"}
                }, {
                    "job_type": "java",
                    "configs": {"conf_key2": "conf_val2"}
                }])

        jobs_create_call = mock.call(name="job_42",
                                     type="java",
                                     description="",
                                     mains=["main_42"],
                                     libs=["lib_42"])

        self.clients("sahara").jobs.create.assert_has_calls(
            [jobs_create_call, jobs_create_call])

        mock_run_job.assert_has_calls([
            mock.call(job_id="42",
                      cluster_id="cl_42",
                      input_id=None,
                      output_id=None,
                      configs={"conf_key": "conf_val"},
                      job_idx=0),
            mock.call(job_id="42",
                      cluster_id="cl_42",
                      input_id=None,
                      output_id=None,
                      configs={"conf_key2": "conf_val2"},
                      job_idx=1)
        ])

    @mock.patch("%s.CreateLaunchJob.generate_random_name" % BASE,
                return_value="job_42")
    @mock.patch("%s.CreateLaunchJobSequenceWithScaling"
                "._scale_cluster" % BASE)
    @mock.patch("%s.CreateLaunchJob._run_job_execution" % BASE)
    def test_create_launch_job_sequence_with_scaling(
            self,
            mock_run_job,
            mock_create_launch_job_sequence_with_scaling__scale_cluster,
            mock_create_launch_job_generate_random_name
    ):
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
        scenario = jobs.CreateLaunchJobSequenceWithScaling(self.context)

        scenario.run(
            jobs=[
                {
                    "job_type": "java",
                    "configs": {"conf_key": "conf_val"}
                }, {
                    "job_type": "java",
                    "configs": {"conf_key2": "conf_val2"}
                }],
            deltas=[1, -1])

        jobs_create_call = mock.call(name="job_42",
                                     type="java",
                                     description="",
                                     mains=["main_42"],
                                     libs=["lib_42"])

        self.clients("sahara").jobs.create.assert_has_calls(
            [jobs_create_call, jobs_create_call])

        je_0 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None, configs={"conf_key": "conf_val"},
                         job_idx=0)
        je_1 = mock.call(job_id="42", cluster_id="cl_42", input_id=None,
                         output_id=None,
                         configs={"conf_key2": "conf_val2"}, job_idx=1)
        mock_run_job.assert_has_calls([je_0, je_1, je_0, je_1, je_0, je_1])
