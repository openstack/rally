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

""" Rally command: verify """

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally.objects import endpoint
from rally.orchestrator import api
from rally import osclients


TEMPEST_TEST_SETS = ('full',
                     'smoke',
                     'baremetal',
                     'compute',
                     'data_processing',
                     'identity',
                     'image',
                     'network',
                     'object_storage',
                     'orchestration',
                     'telemetry',
                     'volume')


class VerifyCommands(object):

    @cliutils.args('--deploy-id', dest='deploy_id', type=str, required=False,
                   help='UUID of a deployment.')
    @cliutils.args('--set', dest='set_name', type=str, required=False,
                   help='Name of tempest test set. '
                        'Available sets: %s' % ', '.join(TEMPEST_TEST_SETS))
    @cliutils.args('--regex', dest='regex', type=str, required=False,
                   help='Regular expression of test.')
    @envutils.with_default_deploy_id
    def start(self, deploy_id=None, set_name='smoke', regex=None):
        """Start running tempest tests against a live cloud cluster.

        :param deploy_id: a UUID of a deployment
        :param set_name: Name of tempest test set
        :param regex: Regular expression of test
        """
        if regex:
            set_name = 'full'
        if set_name not in TEMPEST_TEST_SETS:
            print('Sorry, but there are no desired tempest test set. '
                  'Please choose from: %s' % ', '.join(TEMPEST_TEST_SETS))
            return

        endpoints = db.deployment_get(deploy_id)['endpoints']
        endpoint_dict = endpoints[0]
        clients = osclients.Clients(endpoint.Endpoint(**endpoint_dict))
        glance = clients.glance()

        image_list = []
        for image in glance.images.list():
            if 'cirros' in image.name:
                image_list.append(image)

        #TODO(miarmak): Add ability to upload new images if there are no
        #necessary images in the cloud (cirros)

        try:
            image_id = image_list[0].id
            alt_image_id = image_list[1].id
        except IndexError:
            print('Sorry, but there are no desired images or only one')
            return

        nova = clients.nova()
        flavor_list = []
        for fl in sorted(nova.flavors.list(), key=lambda flavor: flavor.ram):
            flavor_list.append(fl)

        #TODO(miarmak): Add ability to create new flavors if they are missing

        try:
            flavor_id = flavor_list[0].id
            alt_flavor_id = flavor_list[1].id
        except IndexError:
            print('Sorry, but there are no desired flavors or only one')
            return

        #TODO(miarmak): Add getting network and router id's from neutronclient

        api.verify(deploy_id, image_id, alt_image_id, flavor_id, alt_flavor_id,
                   set_name, regex)
