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

import json
import pprint

import six

from rally.cmd import cliutils
from rally.cmd import envutils
from rally import db
from rally import exceptions
from rally import objects
from rally.openstack.common import cliutils as common_cliutils
from rally.openstack.common.gettextutils import _
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
            return(1)

        endpoints = db.deployment_get(deploy_id)['endpoints']
        endpoint_dict = endpoints[0]
        clients = osclients.Clients(objects.Endpoint(**endpoint_dict))
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
            return(1)

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
            return(1)

        #TODO(miarmak): Add getting network and router id's from neutronclient

        api.verify(deploy_id, image_id, alt_image_id, flavor_id, alt_flavor_id,
                   set_name, regex)

    def list(self):
        """Print a result list of verifications."""
        fields = ['UUID', 'Deployment UUID', 'Set name', 'Tests', 'Failures',
                  'Created at', 'Status']
        verifications = db.verification_list()
        if verifications:
            common_cliutils.print_list(verifications, fields, sortby_index=6)
        else:
            print(_("There are no results from verifier. To run a verifier, "
                    "use:\nrally verify start"))

    @cliutils.args('--uuid', type=str, dest='verification_uuid',
                   help='UUID of the verification')
    @cliutils.args('--pretty', type=str, help=('pretty print (pprint) '
                                               'or json print (json)'))
    def results(self, verification_uuid, pretty=False):
        """Print raw results of verification.

        :param verification_uuid: Verification UUID
        :param pretty: Pretty print (pprint) or not (json)
        """
        try:
            results = db.verification_result_get(verification_uuid)['data']
        except exceptions.NotFoundException as e:
            print(e.message)
            return 1

        if not pretty or pretty == 'json':
            print(json.dumps(results))
        elif pretty == 'pprint':
            print()
            pprint.pprint(results)
            print()
        else:
            print(_("Wrong value for --pretty=%s") % pretty)

    @cliutils.args('--uuid', dest='verification_uuid', type=str,
                   required=False,
                   help='UUID of a verification')
    @cliutils.args('--sort-by', dest='sort_by', type=str, required=False,
                   help='Tests can be sorted by "name" or "duration"')
    @cliutils.args('--detailed', dest='detailed', action='store_true',
                   required=False, help='Prints traceback of failed tests')
    def show(self, verification_uuid, sort_by='name', detailed=False):
        try:
            sortby_index = ('name', 'duration').index(sort_by)
        except ValueError:
            print("Sorry, but verification results can't be sorted "
                  "by '%s'." % sort_by)
            return 1

        try:
            verification = db.verification_get(verification_uuid)
            tests = db.verification_result_get(verification_uuid)
        except exceptions.NotFoundException as e:
            print(e.message)
            return 1

        print ("Total results of verification:\n")
        total_fields = ['UUID', 'Deployment UUID', 'Set name', 'Tests',
                        'Failures', 'Created at', 'Status']
        common_cliutils.print_list([verification], fields=total_fields)

        print ("\nTests:\n")
        fields = ['name', 'time', 'status']

        values = map(objects.Verification,
                     six.itervalues(tests.data['test_cases']))
        common_cliutils.print_list(values, fields, sortby_index=sortby_index)

        if detailed:
            for test in six.itervalues(tests.data['test_cases']):
                if test['status'] == 'FAIL':
                    formatted_test = (
                        '====================================================='
                        '=================\n'
                        'FAIL: %(name)s\n'
                        'Time: %(time)s\n'
                        'Type: %(type)s\n'
                        '-----------------------------------------------------'
                        '-----------------\n'
                        '%(log)s\n'
                    ) % {
                        'name': test['name'], 'time': test['time'],
                        'type': test['failure']['type'],
                        'log': test['failure']['log']}
                    print (formatted_test)

    @cliutils.args('--uuid', dest='verification_uuid', type=str,
                   required=False,
                   help='UUID of a verification')
    @cliutils.args('--sort-by', dest='sort_by', type=str, required=False,
                   help='Tests can be sorted by "name" or "duration"')
    def detailed(self, verification_uuid, sort_by='name'):
        self.show(verification_uuid, sort_by, True)
