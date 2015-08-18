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

from rally import exceptions
from rally.task import types
from tests.unit import fakes
from tests.unit import test


class FlavorResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(FlavorResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.tiny",
                                                              id="1"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.nano",
                                                              id="42"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.large",
                                                              id="44"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.large",
                                                              id="45"))

    def test_transform_by_id(self):
        resource_config = {"id": "42"}
        flavor_id = types.FlavorResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_id_from_base_class(self):
        resource_config = {}
        types.ResourceType.transform(
            clients=self.clients, resource_config=resource_config)

    def test_transform_by_name(self):
        resource_config = {"name": "m1.nano"}
        flavor_id = types.FlavorResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "m1.medium"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FlavorResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_name_multiple_match(self):
        resource_config = {"name": "m1.large"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FlavorResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "m(1|2)\.nano"}
        flavor_id = types.FlavorResourceType.transform(
            clients=self.clients, resource_config=resource_config)
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


class EC2FlavorResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(EC2FlavorResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.tiny",
                                                              id="1"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.nano",
                                                              id="2"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.large",
                                                              id="3"))
        self.clients.nova().flavors._cache(fakes.FakeResource(name="m1.xlarge",
                                                              id="3"))

    def test_transform_by_name(self):
        resource_config = {"name": "m1.nano"}
        flavor_name = types.EC2FlavorResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_name, "m1.nano")

    def test_transform_by_id(self):
        resource_config = {"id": "2"}
        flavor_name = types.EC2FlavorResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_name, "m1.nano")

    def test_transform_by_id_no_match(self):
        resource_config = {"id": "4"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2FlavorResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_id_multiple_match(self):
        resource_config = {"id": "3"}
        self.assertRaises(exceptions.MultipleMatchesFound,
                          types.EC2FlavorResourceType.transform, self.clients,
                          resource_config)


class ImageResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(ImageResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        image1 = fakes.FakeResource(name="cirros-0.3.4-uec", id="100")
        self.clients.glance().images._cache(image1)
        image2 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk", id="101")
        self.clients.glance().images._cache(image2)
        image3 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                    id="102")
        self.clients.glance().images._cache(image3)
        image4 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                    id="103")
        self.clients.glance().images._cache(image4)

    def test_transform_by_id(self):
        resource_config = {"id": "100"}
        image_id = types.ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name(self):
        resource_config = {"name": "^cirros-0.3.4-uec$"}
        image_id = types.ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "cirros-0.3.4-uec-boot"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_name_match_multiple(self):
        resource_config = {"name": "cirros-0.3.4-uec-ramdisk-copy"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "-uec$"}
        image_id = types.ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
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


class EC2ImageResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(EC2ImageResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        image1 = fakes.FakeResource(name="cirros-0.3.4-uec", id="100")
        self.clients.glance().images._cache(image1)
        image2 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk", id="102")
        self.clients.glance().images._cache(image2)
        image3 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                    id="102")
        self.clients.glance().images._cache(image3)
        image4 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                    id="103")
        self.clients.glance().images._cache(image4)

        ec2_image1 = fakes.FakeResource(name="cirros-0.3.4-uec", id="200")
        ec2_image2 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk",
                                        id="201")
        ec2_image3 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                        id="202")
        ec2_image4 = fakes.FakeResource(name="cirros-0.3.4-uec-ramdisk-copy",
                                        id="203")

        self.clients.ec2().get_all_images = mock.Mock(
            return_value=[ec2_image1, ec2_image2, ec2_image3, ec2_image4])

    def test_transform_by_name(self):
        resource_config = {"name": "^cirros-0.3.4-uec$"}
        ec2_image_id = types.EC2ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_id(self):
        resource_config = {"id": "100"}
        ec2_image_id = types.EC2ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_id_no_match(self):
        resource_config = {"id": "101"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_id_match_multiple(self):
        resource_config = {"id": "102"}
        self.assertRaises(exceptions.MultipleMatchesFound,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "cirros-0.3.4-uec-boot"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_name_match_multiple(self):
        resource_config = {"name": "cirros-0.3.4-uec-ramdisk-copy"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "-uec$"}
        ec2_image_id = types.EC2ImageResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_regex_match_multiple(self):
        resource_config = {"regex": "^cirros"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "-boot$"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2ImageResourceType.transform, self.clients,
                          resource_config)


class VolumeTypeResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(VolumeTypeResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        volume_type1 = fakes.FakeResource(name="lvmdriver-1", id=100)
        self.clients.cinder().volume_types._cache(volume_type1)

    def test_transform_by_id(self):
        resource_config = {"id": 100}
        volumetype_id = types.VolumeTypeResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name(self):
        resource_config = {"name": "lvmdriver-1"}
        volumetype_id = types.VolumeTypeResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "nomatch-1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeTypeResourceType.transform,
                          self.clients, resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "^lvm.*-1"}
        volumetype_id = types.VolumeTypeResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "dd"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeTypeResourceType.transform,
                          self.clients, resource_config)


class NeutronNetworkResourceTypeTestCase(test.TestCase):

    def setUp(self):
        super(NeutronNetworkResourceTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        net1_data = {"network": {
            "name": "net1"
        }}
        network1 = self.clients.neutron().create_network(net1_data)
        self.net1_id = network1["network"]["id"]

    def test_transform_by_id(self):
        resource_config = {"id": self.net1_id}
        network_id = types.NeutronNetworkResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(network_id, self.net1_id)

    def test_transform_by_name(self):
        resource_config = {"name": "net1"}
        network_id = types.NeutronNetworkResourceType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(network_id, self.net1_id)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "nomatch-1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.NeutronNetworkResourceType.transform,
                          self.clients, resource_config)


class PreprocessTestCase(test.TestCase):

    @mock.patch("rally.task.types.scenario.Scenario.get")
    @mock.patch("rally.task.types.osclients")
    def test_preprocess(self, mock_osclients, mock_scenario_get):

        name = "some_plugin"

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

        mock_scenario_get.return_value._meta_get.return_value = {
            "a": Preprocessor
        }

        result = types.preprocess(name, context, args)
        mock_scenario_get.assert_called_once_with(name)
        mock_scenario_get.return_value._meta_get.assert_called_once_with(
            "preprocessors", default={})
        mock_osclients.Clients.assert_called_once_with(
            context["admin"]["endpoint"])
        self.assertEqual({"a": 20, "b": 20}, result)


class FilePathOrUrlTypeTestCase(test.TestCase):

    @mock.patch("rally.task.types.os.path.isfile")
    @mock.patch("rally.task.types.requests")
    def test_transform_file(self, mock_requests, mock_isfile):
        mock_isfile.return_value = True
        path = types.FilePathOrUrlType.transform(None, "fake_path")
        self.assertEqual("fake_path", path)
        mock_isfile.return_value = False
        mock_requests.head.return_value = mock.Mock(status_code=500)
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.FilePathOrUrlType.transform,
                          None, "fake_path")
        mock_requests.head.assert_called_once_with("fake_path")

    @mock.patch("rally.task.types.os.path.isfile")
    @mock.patch("rally.task.types.requests")
    def test_transform_url(self, mock_requests, mock_isfile):
        mock_isfile.return_value = False
        mock_requests.head.return_value = mock.Mock(status_code=200)
        path = types.FilePathOrUrlType.transform(None, "fake_url")
        self.assertEqual("fake_url", path)


class FileTypeTestCase(test.TestCase):

    @mock.patch("rally.task.types.open",
                side_effect=mock.mock_open(read_data="file_context"),
                create=True)
    def test_transform_by_path(self, mock_open):
        resource_config = "file.yaml"
        file_context = types.FileType.transform(
            clients=None, resource_config=resource_config)
        self.assertEqual(file_context, "file_context")

    @mock.patch("rally.task.types.open",
                side_effect=IOError, create=True)
    def test_transform_by_path_no_match(self, mock_open):
        resource_config = "nonexistant.yaml"
        self.assertRaises(IOError,
                          types.FileType.transform,
                          clients=None,
                          resource_config=resource_config)


class FileTypeDictTestCase(test.TestCase):

    @mock.patch("rally.task.types.open",
                side_effect=mock.mock_open(read_data="file_context"),
                create=True)
    def test_transform_by_path(self, mock_open):
        resource_config = ["file.yaml"]
        file_context = types.FileTypeDict.transform(
            clients=None,
            resource_config=resource_config)
        self.assertEqual(file_context, {"file.yaml": "file_context"})

    @mock.patch("rally.task.types.open",
                side_effect=IOError, create=True)
    def test_transform_by_path_no_match(self, mock_open):
        resource_config = ["nonexistant.yaml"]
        self.assertRaises(IOError,
                          types.FileTypeDict.transform,
                          clients=None,
                          resource_config=resource_config)
