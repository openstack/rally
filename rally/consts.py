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
    RPS = "rps"


class _Service(utils.ImmutableMixin, utils.EnumMixin):
    """OpenStack services names, by rally convention."""

    NOVA = "nova"
    NOVAV3 = "novav3"
    CINDER = "cinder"
    CINDERV2 = "cinderv2"
    EC2 = "ec2"
    GLANCE = "glance"
    CLOUD = "cloud"
    HEAT = "heat"
    KEYSTONE = "keystone"
    NEUTRON = "neutron"
    CEILOMETER = "ceilometer"
    S3 = "s3"
    TROVE = "trove"


class _ServiceType(utils.ImmutableMixin, utils.EnumMixin):
    """OpenStack services types, mapped to service names."""

    VOLUME = "volume"
    VOLUMEV2 = "volumev2"
    EC2 = "ec2"
    IMAGE = "image"
    CLOUD = "cloudformation"
    ORCHESTRATION = "orchestration"
    IDENTITY = "identity"
    COMPUTE = "compute"
    COMPUTEV3 = "computev3"
    NETWORK = "network"
    METERING = "metering"
    S3 = "s3"
    DATABASE = "database"

    def __init__(self):
        self.__names = {
            self.COMPUTE: _Service.NOVA,
            self.COMPUTEV3: _Service.NOVAV3,
            self.VOLUME: _Service.CINDER,
            self.VOLUMEV2: _Service.CINDER,
            self.EC2: _Service.EC2,
            self.IMAGE: _Service.GLANCE,
            self.CLOUD: _Service.CLOUD,
            self.ORCHESTRATION: _Service.HEAT,
            self.IDENTITY: _Service.KEYSTONE,
            self.NETWORK: _Service.NEUTRON,
            self.METERING: _Service.CEILOMETER,
            self.S3: _Service.S3,
            self.DATABASE: _Service.TROVE
        }

    def __getitem__(self, service_type):
        """Mapping protocol to service names.

        :param name: str, service name
        :returns: str, service type
        """
        return self.__names[service_type]


TaskStatus = _TaskStatus()
DeployStatus = _DeployStatus()
EndpointPermission = _EndpointPermission()
RunnerType = _RunnerType()
ServiceType = _ServiceType()
Service = _Service()
