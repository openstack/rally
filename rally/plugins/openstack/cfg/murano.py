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
    cfg.IntOpt("murano_deploy_environment_timeout",
               default=1200,
               deprecated_name="deploy_environment_timeout",
               deprecated_group="benchmark",
               help="A timeout in seconds for an environment deploy"),
    cfg.IntOpt("murano_deploy_environment_check_interval",
               default=5,
               deprecated_name="deploy_environment_check_interval",
               deprecated_group="benchmark",
               help="Deploy environment check interval in seconds"),
]}
