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


import unittest

from tests.functional import utils


class ShowTestCase(unittest.TestCase):

    def setUp(self):
        super(ShowTestCase, self).setUp()
        self.rally = utils.Rally()

    def test_show_images(self):
        res = self.rally("show images")
        cirros = "cirros" in res
        testvm = "TestVM" in res
        self.assertTrue(cirros or testvm)

    def test_show_flavors(self):
        res = self.rally("show flavors")
        self.assertIn("m1.tiny", res)

    def test_show_networks(self):
        res = self.rally("show networks")
        private = "private" in res
        novanetwork = "novanetwork" in res
        self.assertTrue(private or novanetwork)

    def test_show_secgroups(self):
        res = self.rally("show secgroups")
        self.assertIn("default", res)

    def test_show_keypairs(self):
        self.rally("show keypairs")
