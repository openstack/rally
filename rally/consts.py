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

"""
There is a lot of situation when we would like to work with Enum or consts.
E.g. work around Tasks. We would like to use Enum in DB to store status of task
and also in migration that creates DB and in business logic to set some status
so to avoid copy paste or dirrect usage of enums values we create singltons
for each enum. (e.g TaskStatus)
"""

from rally import utils


TEMPEST_TEST_SETS = ("full",
                     "smoke",
                     "baremetal",
                     "compute",
                     "data_processing",
                     "identity",
                     "image",
                     "network",
                     "object_storage",
                     "orchestration",
                     "telemetry",
                     "volume")


class _TaskStatus(utils.ImmutableMixin, utils.EnumMixin):
    INIT = "init"
    VERIFYING = "verifying"
    SETTING_UP = "setting up"
    RUNNING = "running"
    CLEANING_UP = "cleaning up"
    FINISHED = "finished"
    FAILED = "failed"


class _DeployStatus(utils.ImmutableMixin, utils.EnumMixin):
    DEPLOY_INIT = 'deploy->init'
    DEPLOY_STARTED = 'deploy->started'
    DEPLOY_SUBDEPLOY = 'deploy->subdeploy'
    DEPLOY_FINISHED = 'deploy->finished'
    DEPLOY_FAILED = 'deploy->failed'

    DEPLOY_INCONSISTENT = 'deploy->inconsistent'

    CLEANUP_STARTED = 'cleanup->started'
    CLEANUP_FINISHED = 'cleanup->finished'
    CLEANUP_FAILED = 'cleanup->failed'


class _EndpointPermission(utils.ImmutableMixin, utils.EnumMixin):
    ADMIN = "admin"
    USER = "user"


class _RunnerType(utils.ImmutableMixin, utils.EnumMixin):
    SERIAL = "serial"
    CONSTANT = "constant"
    CONSTANT_FOR_DURATION = "constant_for_duration"
    PERIODIC = "periodic"


TaskStatus = _TaskStatus()
DeployStatus = _DeployStatus()
EndpointPermission = _EndpointPermission()
RunnerType = _RunnerType()
