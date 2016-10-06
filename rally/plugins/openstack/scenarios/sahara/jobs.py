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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.sahara import utils
from rally.task import validation

LOG = logging.getLogger(__name__)


"""Benchmark scenarios for Sahara jobs."""


@validation.required_services(consts.Service.SAHARA)
@validation.required_contexts("users", "sahara_image",
                              "sahara_job_binaries", "sahara_cluster")
@scenario.configure(context={"cleanup": ["sahara"]},
                    name="SaharaJob.create_launch_job")
class CreateLaunchJob(utils.SaharaScenario):

    def run(self, job_type, configs, job_idx=0):
        """Create and execute a Sahara EDP Job.

        This scenario Creates a Job entity and launches an execution on a
        Cluster.

        :param job_type: type of the Data Processing Job
        :param configs: config dict that will be passed to a Job Execution
        :param job_idx: index of a job in a sequence. This index will be
                        used to create different atomic actions for each job
                        in a sequence
        """

        mains = self.context["tenant"]["sahara"]["mains"]
        libs = self.context["tenant"]["sahara"]["libs"]

        name = self.generate_random_name()
        job = self.clients("sahara").jobs.create(name=name,
                                                 type=job_type,
                                                 description="",
                                                 mains=mains,
                                                 libs=libs)

        cluster_id = self.context["tenant"]["sahara"]["cluster"]

        if job_type.lower() == "java":
            input_id = None
            output_id = None
        else:
            input_id = self.context["tenant"]["sahara"]["input"]
            output_id = self._create_output_ds().id

        self._run_job_execution(job_id=job.id,
                                cluster_id=cluster_id,
                                input_id=input_id,
                                output_id=output_id,
                                configs=configs,
                                job_idx=job_idx)


@validation.required_services(consts.Service.SAHARA)
@validation.required_contexts("users", "sahara_image",
                              "sahara_job_binaries", "sahara_cluster")
@scenario.configure(context={"cleanup": ["sahara"]},
                    name="SaharaJob.create_launch_job_sequence")
class CreateLaunchJobSequence(utils.SaharaScenario):

    def run(self, jobs):
        """Create and execute a sequence of the Sahara EDP Jobs.

        This scenario Creates a Job entity and launches an execution on a
        Cluster for every job object provided.

        :param jobs: list of jobs that should be executed in one context
        """

        launch_job = CreateLaunchJob(self.context)

        for idx, job in enumerate(jobs):
            LOG.debug("Launching Job. Sequence #%d" % idx)
            launch_job.run(job["job_type"], job["configs"], idx)


@validation.required_services(consts.Service.SAHARA)
@validation.required_contexts("users", "sahara_image",
                              "sahara_job_binaries", "sahara_cluster")
@scenario.configure(context={"cleanup": ["sahara"]},
                    name="SaharaJob.create_launch_job_sequence_with_scaling")
class CreateLaunchJobSequenceWithScaling(utils.SaharaScenario,):

    def run(self, jobs, deltas):
        """Create and execute Sahara EDP Jobs on a scaling Cluster.

        This scenario Creates a Job entity and launches an execution on a
        Cluster for every job object provided. The Cluster is scaled according
        to the deltas values and the sequence is launched again.

        :param jobs: list of jobs that should be executed in one context
        :param deltas: list of integers which will be used to add or
                       remove worker nodes from the cluster
        """

        cluster_id = self.context["tenant"]["sahara"]["cluster"]

        launch_job_sequence = CreateLaunchJobSequence(self.context)
        launch_job_sequence.run(jobs)

        for delta in deltas:
            # The Cluster is fetched every time so that its node groups have
            # correct 'count' values.
            cluster = self.clients("sahara").clusters.get(cluster_id)

            LOG.debug("Scaling cluster %s with delta %d" %
                      (cluster.name, delta))
            if delta == 0:
                # Zero scaling makes no sense.
                continue
            elif delta > 0:
                self._scale_cluster_up(cluster, delta)
            elif delta < 0:
                self._scale_cluster_down(cluster, delta)

            LOG.debug("Starting Job sequence")
            launch_job_sequence.run(jobs)