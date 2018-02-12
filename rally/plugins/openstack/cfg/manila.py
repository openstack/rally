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
    cfg.FloatOpt(
        "manila_share_create_prepoll_delay",
        default=2.0,
        deprecated_group="benchmark",
        help="Delay between creating Manila share and polling for its "
             "status."),
    cfg.FloatOpt(
        "manila_share_create_timeout",
        default=300.0,
        deprecated_group="benchmark",
        help="Timeout for Manila share creation."),
    cfg.FloatOpt(
        "manila_share_create_poll_interval",
        default=3.0,
        deprecated_group="benchmark",
        help="Interval between checks when waiting for Manila share "
             "creation."),
    cfg.FloatOpt(
        "manila_share_delete_timeout",
        default=180.0,
        deprecated_group="benchmark",
        help="Timeout for Manila share deletion."),
    cfg.FloatOpt(
        "manila_share_delete_poll_interval",
        default=2.0,
        deprecated_group="benchmark",
        help="Interval between checks when waiting for Manila share "
             "deletion."),
    cfg.FloatOpt(
        "manila_access_create_timeout",
        default=300.0,
        deprecated_group="benchmark",
        help="Timeout for Manila access creation."),
    cfg.FloatOpt(
        "manila_access_create_poll_interval",
        default=3.0,
        deprecated_group="benchmark",
        help="Interval between checks when waiting for Manila access "
             "creation."),
    cfg.FloatOpt(
        "manila_access_delete_timeout",
        default=180.0,
        deprecated_group="benchmark",
        help="Timeout for Manila access deletion."),
    cfg.FloatOpt(
        "manila_access_delete_poll_interval",
        default=2.0,
        deprecated_group="benchmark",
        help="Interval between checks when waiting for Manila access "
             "deletion."),
]}
