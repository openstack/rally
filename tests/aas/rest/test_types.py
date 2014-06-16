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

"""Test for rest types."""

from __future__ import print_function

from rally.aas.rest import types
from tests import test


class TestLink(test.TestCase):

    def test_make_link(self):
        url = "http://localhost:8877"
        rel = "version"
        link = types.Link.make_link(rel, url, "fake")
        self.assertEqual("http://localhost:8877/fake", link.href)
        self.assertEqual(rel, link.rel)


class TestMediaType(test.TestCase):

    def test_init(self):
        base = "application/json"
        _type = "application/vnd.openstack.rally.v1+json"
        mt = types.MediaType(base, _type)
        self.assertEqual(base, mt.base)
        self.assertEqual(_type, mt.type)


class TestVersion(test.TestCase):

    def test_convert(self):
        id = "v1"
        status = "active"
        updated_at = "2014-01-07T00:00:00Z"
        link = types.Link.make_link("version", "http://localhost:8877", "fake")
        version = types.Version.convert(id, status, updated_at=updated_at,
                                        links=[link])
        self.assertEqual(id, version.id)
        self.assertEqual(status, version.status)
        self.assertEqual(updated_at, version.updated_at)
        self.assertEqual("application/json", version.media_types[0].base)
        self.assertEqual("application/vnd.openstack.rally.v1+json",
                         version.media_types[0].type)
        self.assertEqual([link], version.links)
