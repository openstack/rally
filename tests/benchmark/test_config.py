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

"""Tests for config managers."""
from rally.benchmark import config
from rally import test


class CloudConfigManagerTestCase(test.NoDBTestCase):

    def setUp(self):
        super(CloudConfigManagerTestCase, self).setUp()
        self.manager = config.CloudConfigManager()

    def test_defaults(self):
        self.assertTrue(self.manager.has_section('identity'))
        self.assertTrue(self.manager.has_section('compute'))
        # TODO(msdubov): Don't know exactly which sections
        #                should always be there

    def test_to_dict(self):
        self.manager.add_section('dummy_section')
        self.manager.set('dummy_section', 'dummy_option', 'dummy_value')
        dct = self.manager.to_dict()
        self.assertTrue('dummy_section' in dct)
        self.assertEquals(dct['dummy_section']['dummy_option'], 'dummy_value')

    def test_read_from_dict(self):
        dct = {'dummy_section': {'dummy_option': 'dummy_value'}}
        self.manager.read_from_dict(dct)
        self.assertTrue(self.manager.has_section('dummy_section'))
        self.assertEquals(self.manager.get('dummy_section', 'dummy_option'),
                          'dummy_value')
