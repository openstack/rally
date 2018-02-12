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
    cfg.FloatOpt("magnum_cluster_create_prepoll_delay",
                 default=5.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for the status."),
    cfg.FloatOpt("magnum_cluster_create_timeout",
                 default=2400.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for magnum cluster to be "
                      "created."),
    cfg.FloatOpt("magnum_cluster_create_poll_interval",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "cluster creation."),
    cfg.FloatOpt("k8s_pod_create_timeout",
                 default=1200.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for k8s pod to be created."),
    cfg.FloatOpt("k8s_pod_create_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "k8s pod creation."),
    cfg.FloatOpt("k8s_rc_create_timeout",
                 default=1200.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for k8s rc to be created."),
    cfg.FloatOpt("k8s_rc_create_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "k8s rc creation.")
]}
