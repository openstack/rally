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
    cfg.FloatOpt("heat_stack_create_prepoll_delay",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for it status."),
    cfg.FloatOpt("heat_stack_create_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for heat stack to be created."),
    cfg.FloatOpt("heat_stack_create_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack creation."),
    cfg.FloatOpt("heat_stack_delete_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for heat stack to be deleted."),
    cfg.FloatOpt("heat_stack_delete_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack deletion."),
    cfg.FloatOpt("heat_stack_check_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack to be checked."),
    cfg.FloatOpt("heat_stack_check_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack checking."),
    cfg.FloatOpt("heat_stack_update_prepoll_delay",
                 default=2.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to sleep after updating a resource before "
                      "polling for it status."),
    cfg.FloatOpt("heat_stack_update_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack to be updated."),
    cfg.FloatOpt("heat_stack_update_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack update."),
    cfg.FloatOpt("heat_stack_suspend_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack to be suspended."),
    cfg.FloatOpt("heat_stack_suspend_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack suspend."),
    cfg.FloatOpt("heat_stack_resume_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack to be resumed."),
    cfg.FloatOpt("heat_stack_resume_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack resume."),
    cfg.FloatOpt("heat_stack_snapshot_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack snapshot to "
                      "be created."),
    cfg.FloatOpt("heat_stack_snapshot_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack snapshot to be created."),
    cfg.FloatOpt("heat_stack_restore_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time(in sec) to wait for stack to be restored from "
                      "snapshot."),
    cfg.FloatOpt("heat_stack_restore_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval(in sec) between checks when waiting for "
                      "stack to be restored."),
    cfg.FloatOpt("heat_stack_scale_timeout",
                 default=3600.0,
                 deprecated_group="benchmark",
                 help="Time (in sec) to wait for stack to scale up or down."),
    cfg.FloatOpt("heat_stack_scale_poll_interval",
                 default=1.0,
                 deprecated_group="benchmark",
                 help="Time interval (in sec) between checks when waiting for "
                      "a stack to scale up or down.")
]}
