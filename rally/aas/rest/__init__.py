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

from oslo_config import cfg


REST_SERVICE_OPTS = [
    cfg.IntOpt("port",
               default=8877,
               help="The port for the Rally API server",
               ),
    cfg.StrOpt("host",
               default="0.0.0.0",
               help="The listen IP for the Rally API server",
               ),
]
REST_OPT_GROUP = cfg.OptGroup(name="rest",
                              title="Options for the openstack-rally-api "
                                    "service")

CONF = cfg.CONF
CONF.register_group(REST_OPT_GROUP)
CONF.register_opts(REST_SERVICE_OPTS, REST_OPT_GROUP)
