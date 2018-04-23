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

import copy

from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions
from rally.plugins.openstack import osclients
from rally.plugins.openstack.services.image import image
from rally.plugins.openstack.services.storage import block
from rally.task import types


LOG = logging.getLogger(__name__)


class OpenStackResourceType(types.ResourceType):
    """A base class for OpenStack ResourceTypes plugins with help-methods"""
    def __init__(self, context, cache=None):
        super(OpenStackResourceType, self).__init__(context, cache)
        self._clients = None
        if self._context.get("admin"):
            self._clients = osclients.Clients(
                self._context["admin"]["credential"])
        elif self._context.get("users"):
            self._clients = osclients.Clients(
                self._context["users"][0]["credential"])


@plugin.configure(name="nova_flavor")
class Flavor(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Nova's flavor ID by name or regexp."""

    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        if not resource_id:
            novaclient = self._clients.nova()
            resource_id = types._id_from_name(
                resource_config=resource_spec,
                resources=novaclient.flavors.list(),
                typename="flavor")
        return resource_id


@plugin.configure(name="ec2_flavor")
class EC2Flavor(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Nova's flavor Name by it's ID or regexp."""

    def pre_process(self, resource_spec, config):
        resource_name = resource_spec.get("name")
        if not resource_name:
            # NOTE(wtakase): gets resource name from OpenStack id
            novaclient = self._clients.nova()
            resource_name = types._name_from_id(
                resource_config=resource_spec,
                resources=novaclient.flavors.list(),
                typename="flavor")
        return resource_name


@plugin.configure(name="glance_image")
class GlanceImage(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Glance's image ID by name or regexp."""

    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        list_kwargs = resource_spec.get("list_kwargs", {})

        if not resource_id:
            cache_id = hash(frozenset(list_kwargs.items()))
            if cache_id not in self._cache:
                glance = image.Image(self._clients)
                self._cache[cache_id] = glance.list_images(**list_kwargs)
            images = self._cache[cache_id]
            resource_id = types._id_from_name(
                resource_config=resource_spec,
                resources=images,
                typename="image")
        return resource_id


@plugin.configure(name="glance_image_args")
class GlanceImageArguments(OpenStackResourceType,
                           types.DeprecatedBehaviourMixin):
    """Process Glance image create options to look similar in case of V1/V2."""
    def pre_process(self, resource_spec, config):
        resource_spec = copy.deepcopy(resource_spec)
        if "is_public" in resource_spec:
            if "visibility" in resource_spec:
                resource_spec.pop("is_public")
            else:
                visibility = ("public" if resource_spec.pop("is_public")
                              else "private")
                resource_spec["visibility"] = visibility
        return resource_spec


@plugin.configure(name="ec2_image")
class EC2Image(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find EC2 image ID."""

    def pre_process(self, resource_spec, config):
        if "name" not in resource_spec and "regex" not in resource_spec:
            # NOTE(wtakase): gets resource name from OpenStack id
            glanceclient = self._clients.glance()
            resource_name = types._name_from_id(
                resource_config=resource_spec,
                resources=list(glanceclient.images.list()),
                typename="image")
            resource_spec["name"] = resource_name

        # NOTE(wtakase): gets EC2 resource id from name or regex
        ec2client = self._clients.ec2()
        resource_ec2_id = types._id_from_name(
            resource_config=resource_spec,
            resources=list(ec2client.get_all_images()),
            typename="ec2_image")
        return resource_ec2_id


@plugin.configure(name="cinder_volume_type")
class VolumeType(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Cinder volume type ID by name or regexp."""

    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        if not resource_id:
            cinder = block.BlockStorage(self._clients)
            resource_id = types._id_from_name(
                resource_config=resource_spec,
                resources=cinder.list_types(),
                typename="volume_type")
        return resource_id


@plugin.configure(name="neutron_network")
class NeutronNetwork(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Neutron network ID by it's name."""
    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        if resource_id:
            return resource_id
        else:
            neutronclient = self._clients.neutron()
            for net in neutronclient.list_networks()["networks"]:
                if net["name"] == resource_spec.get("name"):
                    return net["id"]

        raise exceptions.InvalidScenarioArgument(
            "Neutron network with name '{name}' not found".format(
                name=resource_spec.get("name")))


@plugin.configure(name="watcher_strategy")
class WatcherStrategy(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Watcher strategy ID by it's name."""

    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        if not resource_id:
            watcherclient = self._clients.watcher()
            resource_id = types._id_from_name(
                resource_config=resource_spec,
                resources=[watcherclient.strategy.get(
                    resource_spec.get("name"))],
                typename="strategy",
                id_attr="uuid")
        return resource_id


@plugin.configure(name="watcher_goal")
class WatcherGoal(OpenStackResourceType, types.DeprecatedBehaviourMixin):
    """Find Watcher goal ID by it's name."""

    def pre_process(self, resource_spec, config):
        resource_id = resource_spec.get("id")
        if not resource_id:
            watcherclient = self._clients.watcher()
            resource_id = types._id_from_name(
                resource_config=resource_spec,
                resources=[watcherclient.goal.get(resource_spec.get("name"))],
                typename="goal",
                id_attr="uuid")
        return resource_id
