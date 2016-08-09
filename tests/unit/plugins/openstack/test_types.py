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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack import types
from tests.unit import fakes
from tests.unit import test


class FlavorTestCase(test.TestCase):

    def setUp(self):
        super(FlavorTestCase, self).setUp()
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
        flavor_id = types.Flavor.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_name(self):
        resource_config = {"name": "m1.nano"}
        flavor_id = types.Flavor.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "m1.medium"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.Flavor.transform, self.clients,
                          resource_config)

    def test_transform_by_name_multiple_match(self):
        resource_config = {"name": "m1.large"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.Flavor.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "m(1|2)\.nano"}
        flavor_id = types.Flavor.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_id, "42")

    def test_transform_by_regex_multiple_match(self):
        resource_config = {"regex": "^m1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.Flavor.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.Flavor.transform, self.clients,
                          resource_config)


class EC2FlavorTestCase(test.TestCase):

    def setUp(self):
        super(EC2FlavorTestCase, self).setUp()
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
        flavor_name = types.EC2Flavor.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_name, "m1.nano")

    def test_transform_by_id(self):
        resource_config = {"id": "2"}
        flavor_name = types.EC2Flavor.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(flavor_name, "m1.nano")

    def test_transform_by_id_no_match(self):
        resource_config = {"id": "4"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Flavor.transform, self.clients,
                          resource_config)

    def test_transform_by_id_multiple_match(self):
        resource_config = {"id": "3"}
        self.assertRaises(exceptions.MultipleMatchesFound,
                          types.EC2Flavor.transform, self.clients,
                          resource_config)


class GlanceImageTestCase(test.TestCase):

    def setUp(self):
        super(GlanceImageTestCase, self).setUp()
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
        image_id = types.GlanceImage.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name(self):
        resource_config = {"name": "^cirros-0.3.4-uec$"}
        image_id = types.GlanceImage.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "cirros-0.3.4-uec-boot"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.GlanceImage.transform, self.clients,
                          resource_config)

    def test_transform_by_name_match_multiple(self):
        resource_config = {"name": "cirros-0.3.4-uec-ramdisk-copy"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.GlanceImage.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "-uec$"}
        image_id = types.GlanceImage.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(image_id, "100")

    def test_transform_by_regex_match_multiple(self):
        resource_config = {"regex": "^cirros"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.GlanceImage.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "-boot$"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.GlanceImage.transform, self.clients,
                          resource_config)


class EC2ImageTestCase(test.TestCase):

    def setUp(self):
        super(EC2ImageTestCase, self).setUp()
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
        ec2_image_id = types.EC2Image.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_id(self):
        resource_config = {"id": "100"}
        ec2_image_id = types.EC2Image.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_id_no_match(self):
        resource_config = {"id": "101"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Image.transform, self.clients,
                          resource_config)

    def test_transform_by_id_match_multiple(self):
        resource_config = {"id": "102"}
        self.assertRaises(exceptions.MultipleMatchesFound,
                          types.EC2Image.transform, self.clients,
                          resource_config)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "cirros-0.3.4-uec-boot"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Image.transform, self.clients,
                          resource_config)

    def test_transform_by_name_match_multiple(self):
        resource_config = {"name": "cirros-0.3.4-uec-ramdisk-copy"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Image.transform, self.clients,
                          resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "-uec$"}
        ec2_image_id = types.EC2Image.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(ec2_image_id, "200")

    def test_transform_by_regex_match_multiple(self):
        resource_config = {"regex": "^cirros"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Image.transform, self.clients,
                          resource_config)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "-boot$"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.EC2Image.transform, self.clients,
                          resource_config)


class VolumeTypeTestCase(test.TestCase):

    def setUp(self):
        super(VolumeTypeTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        volume_type1 = fakes.FakeResource(name="lvmdriver-1", id=100)
        self.clients.cinder().volume_types._cache(volume_type1)

    def test_transform_by_id(self):
        resource_config = {"id": 100}
        volumetype_id = types.VolumeType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name(self):
        resource_config = {"name": "lvmdriver-1"}
        volumetype_id = types.VolumeType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "nomatch-1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeType.transform,
                          self.clients, resource_config)

    def test_transform_by_regex(self):
        resource_config = {"regex": "^lvm.*-1"}
        volumetype_id = types.VolumeType.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(volumetype_id, 100)

    def test_transform_by_regex_no_match(self):
        resource_config = {"regex": "dd"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.VolumeType.transform,
                          self.clients, resource_config)


class NeutronNetworkTestCase(test.TestCase):

    def setUp(self):
        super(NeutronNetworkTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        net1_data = {"network": {
            "name": "net1"
        }}
        network1 = self.clients.neutron().create_network(net1_data)
        self.net1_id = network1["network"]["id"]

    def test_transform_by_id(self):
        resource_config = {"id": self.net1_id}
        network_id = types.NeutronNetwork.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(network_id, self.net1_id)

    def test_transform_by_name(self):
        resource_config = {"name": "net1"}
        network_id = types.NeutronNetwork.transform(
            clients=self.clients, resource_config=resource_config)
        self.assertEqual(network_id, self.net1_id)

    def test_transform_by_name_no_match(self):
        resource_config = {"name": "nomatch-1"}
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          types.NeutronNetwork.transform,
                          self.clients, resource_config)


@ddt.ddt
class WatcherStrategyTestCase(test.TestCase):

    def setUp(self):
        super(WatcherStrategyTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        self.strategy = self.clients.watcher().strategy._cache(
            fakes.FakeResource(name="dummy", id="1"))

    @ddt.data({"resource_config": {"name": "dummy"}})
    @ddt.unpack
    def test_transform_by_name(self, resource_config=None):
        strategy_id = types.WatcherStrategy.transform(self.clients,
                                                      resource_config)
        self.assertEqual(self.strategy.uuid, strategy_id)

    @ddt.data({"resource_config": {"name": "dummy-1"}})
    @ddt.unpack
    def test_transform_by_name_no_match(self, resource_config=None):
        self.assertRaises(exceptions.RallyException,
                          types.WatcherStrategy.transform,
                          self.clients, resource_config)


@ddt.ddt
class WatcherGoalTestCase(test.TestCase):

    def setUp(self):
        super(WatcherGoalTestCase, self).setUp()
        self.clients = fakes.FakeClients()
        self.goal = self.clients.watcher().goal._cache(
            fakes.FakeResource(name="dummy", id="1"))

    @ddt.data({"resource_config": {"name": "dummy"}})
    @ddt.unpack
    def test_transform_by_name(self, resource_config=None):
        goal_id = types.WatcherGoal.transform(self.clients,
                                              resource_config)
        self.assertEqual(self.goal.uuid, goal_id)

    @ddt.data({"resource_config": {"name": "dummy-1"}})
    @ddt.unpack
    def test_transform_by_name_no_match(self, resource_config=None):
        self.assertRaises(exceptions.RallyException,
                          types.WatcherGoal.transform,
                          self.clients, resource_config)
