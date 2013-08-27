# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
and also in migration that creates DB and in buisness logic to set some status
so to avoid copy paste or dirrect usage of enums values we create singltons
for each enum. (e.g TaskStatus)
"""

import itertools

from rally import exceptions


class _Immutable(object):
    def __setattr__(self, key, value):
        raise exceptions.ImmutableException()


class _Enum(object):
    def __iter__(self):
        for k, v in itertools.imap(lambda x: (x, getattr(self, x)), dir(self)):
            if not k.startswith('_') and isinstance(v, str):
                yield v


class _TaskStatus(_Immutable, _Enum):
    INIT = 'init'
    CLEANUP = 'cleanup'
    FINISHED = 'finished'

    REPO_TOOL_GETTING_REPOS = 'repo_tool->getting_repos'

    DEPLOY_CREATING_VENV = 'deploy->create_venv_to_deploy_openstack'
    DEPLOY_BUILDING_OPENSTACK_IN_VENV = 'deploy->building_openstack_in_venv'
    DEPLOY_BUILDING_IMAGE = 'deploy->building_images_with_openstack'
    DEPLOY_BUILDING_OPENSTACK = 'deploy->building_openstack'
    DEPLOY_STARTING_OPENSTACK = 'deply->starting_openstack'
    DEPLOY_FINISHED = 'deploy->finished'

    VM_PROVIDER_UPLOADING_IMAGE = 'vm_provider->uploading_vm_image'
    VM_PROVIDER_DESTROYING_IMAGE = 'vm_provider->destroying_image'
    VM_PROVIDER_GETTING_VMS = 'vm_provide->:getting_vms'
    VM_PROVIDER_DESTROYING_VMS = 'vm_provider->destroying_vms'

    TEST_TOOL_PATCHING_OPENSTACK = 'test_tool->patching_openstack'
    TEST_TOOL_VERIFY_OPENSTACK = 'test_tool->verify_openstack'
    TEST_TOOL_BENCHMARKING = 'test_tool->benchmarking'
    TEST_TOOL_PROCESSING_RESULTS = 'test_tool->result_processing'


TaskStatus = _TaskStatus()
