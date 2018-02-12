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
    cfg.FloatOpt("cinder_volume_create_prepoll_delay",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Time to sleep after creating a resource before"
                      " polling for it status"),
    cfg.FloatOpt("cinder_volume_create_timeout",
                 default=600.0,
                 deprecated_group="benchmark",
                 help="Time to wait for cinder volume to be created."),
    cfg.FloatOpt("cinder_volume_create_poll_interval",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Interval between checks when waiting for volume"
                      " creation."),
    cfg.FloatOpt("cinder_volume_delete_timeout",
                 default=600.0,
                 deprecated_group="benchmark",
                 help="Time to wait for cinder volume to be deleted."),
    cfg.FloatOpt("cinder_volume_delete_poll_interval",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Interval between checks when waiting for volume"
                      " deletion."),
    cfg.FloatOpt("cinder_backup_restore_timeout",
                 default=600.0,
                 deprecated_group="benchmark",
                 help="Time to wait for cinder backup to be restored."),
    cfg.FloatOpt("cinder_backup_restore_poll_interval",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Interval between checks when waiting for backup"
                      " restoring."),
]}
