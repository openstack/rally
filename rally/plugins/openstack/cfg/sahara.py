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

from rally.common import cfg

OPTS = {"openstack": [
    cfg.IntOpt("sahara_cluster_create_timeout",
               default=1800,
               deprecated_group="benchmark",
               help="A timeout in seconds for a cluster create operation"),
    cfg.IntOpt("sahara_cluster_delete_timeout",
               default=900,
               deprecated_group="benchmark",
               help="A timeout in seconds for a cluster delete operation"),
    cfg.IntOpt("sahara_cluster_check_interval",
               default=5,
               deprecated_group="benchmark",
               help="Cluster status polling interval in seconds"),
    cfg.IntOpt("sahara_job_execution_timeout",
               default=600,
               deprecated_group="benchmark",
               help="A timeout in seconds for a Job Execution to complete"),
    cfg.IntOpt("sahara_job_check_interval",
               default=5,
               deprecated_group="benchmark",
               help="Job Execution status polling interval in seconds"),
    cfg.IntOpt("sahara_workers_per_proxy",
               default=20,
               deprecated_group="benchmark",
               help="Amount of workers one proxy should serve to.")
]}
