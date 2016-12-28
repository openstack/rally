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

import itertools

from rally.common import logging
from rally import osclients
from rally.plugins.openstack.cleanup import base as cleanup_base
from rally.plugins.openstack.context.keystone import roles
from rally.plugins.openstack.context.keystone import users
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.scenarios.ec2 import utils as ec2_utils
from rally.plugins.openstack.scenarios.heat import utils as heat_utils
from rally.plugins.openstack.scenarios.ironic import utils as ironic_utils
from rally.plugins.openstack.scenarios.magnum import utils as magnum_utils
from rally.plugins.openstack.scenarios.manila import utils as manila_utils
from rally.plugins.openstack.scenarios.mistral import utils as mistral_utils
from rally.plugins.openstack.scenarios.monasca import utils as monasca_utils
from rally.plugins.openstack.scenarios.murano import utils as murano_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.plugins.openstack.scenarios.sahara import utils as sahara_utils
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.scenarios.watcher import utils as watcher_utils
from rally.plugins.openstack.verification.tempest import config as tempest_conf
from rally.plugins.openstack.wrappers import glance as glance_utils
from rally.task import engine


def list_opts():
    return [
        ("DEFAULT",
         itertools.chain(logging.DEBUG_OPTS,
                         osclients.OSCLIENTS_OPTS,
                         engine.TASK_ENGINE_OPTS)),
        ("benchmark",
         itertools.chain(cinder_utils.CINDER_BENCHMARK_OPTS,
                         ec2_utils.EC2_BENCHMARK_OPTS,
                         glance_utils.GLANCE_BENCHMARK_OPTS,
                         heat_utils.HEAT_BENCHMARK_OPTS,
                         ironic_utils.IRONIC_BENCHMARK_OPTS,
                         magnum_utils.MAGNUM_BENCHMARK_OPTS,
                         manila_utils.MANILA_BENCHMARK_OPTS,
                         mistral_utils.MISTRAL_BENCHMARK_OPTS,
                         monasca_utils.MONASCA_BENCHMARK_OPTS,
                         murano_utils.MURANO_BENCHMARK_OPTS,
                         nova_utils.NOVA_BENCHMARK_OPTS,
                         sahara_utils.SAHARA_BENCHMARK_OPTS,
                         vm_utils.VM_BENCHMARK_OPTS,
                         watcher_utils.WATCHER_BENCHMARK_OPTS)),
        ("tempest",
         itertools.chain(tempest_conf.TEMPEST_OPTS)),
        ("roles_context", itertools.chain(roles.ROLES_CONTEXT_OPTS)),
        ("users_context", itertools.chain(users.USER_CONTEXT_OPTS)),
        ("cleanup", itertools.chain(cleanup_base.CLEANUP_OPTS))
    ]
