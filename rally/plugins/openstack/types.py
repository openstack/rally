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

from rally.common.plugin import plugin
from rally import exceptions
from rally.task import types


@plugin.configure(name="nova_flavor")
class Flavor(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            novaclient = clients.nova()
            resource_id = types._id_from_name(
                resource_config=resource_config,
                resources=novaclient.flavors.list(),
                typename="flavor")
        return resource_id


@plugin.configure(name="ec2_flavor")
class EC2Flavor(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to name.

        In the case of using EC2 API, flavor name is used for launching
        servers.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: name matching resource
        """
        resource_name = resource_config.get("name")
        if not resource_name:
            # NOTE(wtakase): gets resource name from OpenStack id
            novaclient = clients.nova()
            resource_name = types._name_from_id(
                resource_config=resource_config,
                resources=novaclient.flavors.list(),
                typename="flavor")
        return resource_name


@plugin.configure(name="glance_image")
class GlanceImage(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            glanceclient = clients.glance()
            resource_id = types._id_from_name(
                resource_config=resource_config,
                resources=list(glanceclient.images.list()),
                typename="image")
        return resource_id


@plugin.configure(name="ec2_image")
class EC2Image(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to EC2 id.

        If OpenStack resource id is given, this function gets resource name
        from the id and then gets EC2 resource id from the name.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: EC2 id matching resource
        """
        if "name" not in resource_config and "regex" not in resource_config:
            # NOTE(wtakase): gets resource name from OpenStack id
            glanceclient = clients.glance()
            resource_name = types._name_from_id(
                resource_config=resource_config,
                resources=list(glanceclient.images.list()),
                typename="image")
            resource_config["name"] = resource_name

        # NOTE(wtakase): gets EC2 resource id from name or regex
        ec2client = clients.ec2()
        resource_ec2_id = types._id_from_name(
            resource_config=resource_config,
            resources=list(ec2client.get_all_images()),
            typename="ec2_image")
        return resource_ec2_id


@plugin.configure(name="cinder_volume_type")
class VolumeType(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            cinderclient = clients.cinder()
            resource_id = types._id_from_name(resource_config=resource_config,
                                              resources=cinderclient.
                                              volume_types.list(),
                                              typename="volume_type")
        return resource_id


@plugin.configure(name="neutron_network")
class NeutronNetwork(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if resource_id:
            return resource_id
        else:
            neutronclient = clients.neutron()
            for net in neutronclient.list_networks()["networks"]:
                if net["name"] == resource_config.get("name"):
                    return net["id"]

        raise exceptions.InvalidScenarioArgument(
            "Neutron network with name '{name}' not found".format(
                name=resource_config.get("name")))


@plugin.configure(name="watcher_strategy")
class WatcherStrategy(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            watcherclient = clients.watcher()
            resource_id = types._id_from_name(
                resource_config=resource_config,
                resources=[watcherclient.strategy.get(
                    resource_config.get("name"))],
                typename="strategy",
                id_attr="uuid")
        return resource_id


@plugin.configure(name="watcher_goal")
class WatcherGoal(types.ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            watcherclient = clients.watcher()
            resource_id = types._id_from_name(
                resource_config=resource_config,
                resources=[watcherclient.goal.get(
                    resource_config.get("name"))],
                typename="goal",
                id_attr="uuid")
        return resource_id
