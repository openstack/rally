# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

import mock

from rally.benchmark import types
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


class FlavorResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(FlavorResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        self.clients.nova().flavors._cache(fakes.FakeResource(name='m1.tiny',
                                                              id="1"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name='m1.nano',
                                                              id="42"))

    def test_transform_by_id(self):
        resource_config = {"id": "42"}
        flavor_id = types.FlavorResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_id_from_base_class(self):
        resource_config = {}
        types.ResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)

    def test_transform_by_name(self):
        resource_config = {"name": "m1.nano"}
        flavor_id = types.FlavorResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "m1.medium"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FlavorResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "m(1|2)\.nano"}
        flavor_id = types.FlavorResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_regex_multiple_match(self):
        resource_config = {"regex": "^m1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FlavorResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FlavorResourceType.transform, self.clients,
                          resource_config)


class ImageResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(ImageResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        image1 = fakes.FakeResource(name="cirros-0.3.1-uec", id="100")
        self.clients.glance().images._cache(image1)
        image2 = fakes.FakeResource(name="cirros-0.3.1-uec-ramdisk", id="101")
        self.clients.glance().images._cache(image2)

    def test_transform_by_id(self):
        resource_config = {"id": "100"}
        image_id = types.ImageResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name(self):
        resource_config = {"name": "cirros-0.3.1-uec"}
        image_id = types.ImageResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "cirros-0.3.1-uec-boot"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "-uec$"}
        image_id = types.ImageResourceType.transform(
                    clients=self.clients,
                    resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_regex_match_multiple(self):
        resource_config = {"regex": "^cirros"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "-boot$"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.ImageResourceType.transform, self.clients,
                          resource_config)


class VolumeTypeResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(VolumeTypeResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        volume_type1 = fakes.FakeResource(name='lvmdriver-1', id=100)
        self.clients.cinder().volume_types._cache(volume_type1)

    def test_transform_by_id(self):
        resource_config = {"id": 100}
        volumetype_id = types.VolumeTypeResourceType.transform(
                        clients=self.clients,
                        resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name(self):
        resource_config = {"name": "lvmdriver-1"}
        volumetype_id = types.VolumeTypeResourceType.transform(
                        clients=self.clients,
                        resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "nomatch-1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeTypeResourceType.transform,
                          self.clients, resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "^lvm.*-1"}
        volumetype_id = types.VolumeTypeResourceType.transform(
                        clients=self.clients,
                        resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "dd"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeTypeResourceType.transform,
                          self.clients, resource_config)


class PreprocessTestCase(test.TestCase):

    @mock.patch("rally.benchmark.types.base.Scenario.meta")
    @mock.patch("rally.benchmark.types.osclients")
    def test_preprocess(self, mock_osclients, mock_meta):
        cls = "some_class"
        method_name = "method_name"
        context = {
            "a": 1,
            "b": 2,
            "admin": {"endpoint": mock.MagicMock()}
        }
        args = {"a": 10, "b": 20}

        class Preprocessor(types.ResourceType):

            @classmethod
            def transform(cls, clients, resource_config):
                return resource_config * 2

        mock_meta.return_value = {"a": Preprocessor}
        result = types.preprocess(cls, method_name, context, args)
        mock_meta.assert_called_once_with(cls, default={},
                                          method_name=method_name,
                                          attr_name="preprocessors")
        mock_osclients.Clients.assert_called_once_with(
            context["admin"]["endpoint"])
        self.assertEqual({"a": 20, "b": 20}, result)