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
    cfg.FloatOpt("ironic_node_create_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Interval(in sec) between checks when waiting for node "
                      "creation."),
    cfg.FloatOpt("ironic_node_create_timeout",
                 default=300,
                 deprecated_group="benchmark",
                 help="Ironic node create timeout"),
    cfg.FloatOpt("ironic_node_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Ironic node poll interval"),
    cfg.FloatOpt("ironic_node_delete_timeout",
                 default=300,
                 deprecated_group="benchmark",
                 help="Ironic node create timeout")
]}
