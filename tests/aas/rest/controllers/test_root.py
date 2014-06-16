# Copyright 2014 Kylin Cloud
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

from __future__ import print_function

from tests.aas.rest import base


class TestRoot(base.FunctionalTest):

    def test_get_root(self):
        data = self.get_json('/', path_prefix='')
        self.assertEqual('v1', data['versions'][0]['id'])
        # Check fields are not empty
        [self.assertTrue(f) for f in data.keys()]


class TestV1Root(base.FunctionalTest):

    def test_get_v1_root(self):
        data = self.get_json('/')
        self.assertEqual('v1', data['id'])
        # Check if all known resources are present and there are no extra ones.
        expected_resources = set(['id', 'links', 'media_types', 'status',
                                  'updated_at'])
        actual_resources = set(data.keys())
        # TODO(lyj): There are still no resources in api, we need to add the
        #            related resources here when new api resources added.
        self.assertEqual(expected_resources, actual_resources)

        self.assertIn({'type': 'application/vnd.openstack.rally.v1+json',
                       'base': 'application/json'}, data['media_types'])
