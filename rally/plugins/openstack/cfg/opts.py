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

from rally.plugins.openstack.cfg import cinder
from rally.plugins.openstack.cfg import ec2
from rally.plugins.openstack.cfg import glance
from rally.plugins.openstack.cfg import heat
from rally.plugins.openstack.cfg import ironic
from rally.plugins.openstack.cfg import magnum
from rally.plugins.openstack.cfg import manila
from rally.plugins.openstack.cfg import mistral
from rally.plugins.openstack.cfg import monasca
from rally.plugins.openstack.cfg import murano
from rally.plugins.openstack.cfg import neutron
from rally.plugins.openstack.cfg import nova
from rally.plugins.openstack.cfg import osclients
from rally.plugins.openstack.cfg import profiler
from rally.plugins.openstack.cfg import sahara
from rally.plugins.openstack.cfg import senlin
from rally.plugins.openstack.cfg import vm
from rally.plugins.openstack.cfg import watcher

from rally.plugins.openstack.cfg import tempest

from rally.plugins.openstack.cfg import keystone_roles
from rally.plugins.openstack.cfg import keystone_users

from rally.plugins.openstack.cfg import cleanup


def list_opts():

    opts = {}
    for l_opts in (cinder.OPTS, ec2.OPTS, heat.OPTS, ironic.OPTS, magnum.OPTS,
                   manila.OPTS, mistral.OPTS, monasca.OPTS, murano.OPTS,
                   nova.OPTS, osclients.OPTS, profiler.OPTS, sahara.OPTS,
                   vm.OPTS, glance.OPTS, watcher.OPTS, tempest.OPTS,
                   keystone_roles.OPTS, keystone_users.OPTS, cleanup.OPTS,
                   senlin.OPTS, neutron.OPTS):
        for category, opt in l_opts.items():
            opts.setdefault(category, [])
            opts[category].extend(opt)
    return opts
