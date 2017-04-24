# Copyright 2017: Mirantis Inc.
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

import re

from glanceclient import exc as glance_exc

from rally.common import logging
from rally.common import validation
from rally import exceptions
from rally.plugins.openstack import types as openstack_types

LOG = logging.getLogger(__name__)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="image_exists", namespace="openstack")
class ImageExistsValidator(validation.Validator):

    def __init__(self, param_name, nullable):
        """Validator checks existed image or not

        :param param_name: defines which variable should be used
                           to get image id value.
        :param nullable: defines image id param is required
        """
        super(ImageExistsValidator, self).__init__()
        self.param_name = param_name
        self.nullable = nullable

    def validate(self, config, credentials, plugin_cls,
                 plugin_cfg):

        image_args = config.get("args", {}).get(self.param_name)

        if not image_args and self.nullable:
            return

        image_context = config.get("context", {}).get("images", {})
        image_ctx_name = image_context.get("image_name")

        if not image_args:
            message = ("Parameter %s is not specified.") % self.param_name
            return self.fail(message)

        if "image_name" in image_context:
            # NOTE(rvasilets) check string is "exactly equal to" a regex
            # or image name from context equal to image name from args
            if "regex" in image_args:
                match = re.match(image_args.get("regex"), image_ctx_name)
            if image_ctx_name == image_args.get("name") or (
                    "regex" in image_args and match):
                return
        try:
            for user in credentials["openstack"]["users"]:
                clients = user.get("credential", {}).clients()
                image_id = openstack_types.GlanceImage.transform(
                    clients=clients, resource_config=image_args)
                clients.glance().images.get(image_id)
        except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
            message = ("Image '%s' not found") % image_args
            return self.fail(message)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="external_network_exists", namespace="openstack")
class ExternalNetworkExistsValidator(validation.Validator):

    def __init__(self, param_name):
        """Validator checks that external network with given name exists.

        :param param_name: name of validated network
        """
        super(ExternalNetworkExistsValidator, self).__init__()
        self.param_name = param_name

    def validate(self, config, credentials, plugin_cls, plugin_cfg):

        ext_network = config.get("args", {}).get(self.param_name)
        if not ext_network:
            return

        users = credentials["openstack"]["users"]
        result = []
        for user in users:
            creds = user["credential"]

            networks = creds.clients().neutron().list_networks()["networks"]
            external_networks = [net["name"] for net in networks if
                                 net.get("router:external", False)]
            if ext_network not in external_networks:
                message = ("External (floating) network with name {1} "
                           "not found by user {0}. "
                           "Available networks: {2}").format(creds.username,
                                                             ext_network,
                                                             networks)
                result.append(message)
        if result:
            return self.fail(result)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_neutron_extensions",
                      namespace="openstack")
class RequiredNeutronExtensionsValidator(validation.Validator):

    def __init__(self, extensions, *args):
        """Validator checks if the specified Neutron extension is available

        :param extensions: list of Neutron extensions
        """
        super(RequiredNeutronExtensionsValidator, self).__init__()
        if isinstance(extensions, (list, tuple)):
            # services argument is a list, so it is a new way of validators
            #  usage, args in this case should not be provided
            self.req_ext = extensions
            if args:
                LOG.warning("Positional argument is not what "
                            "'required_neutron_extensions' decorator expects. "
                            "Use `extensions` argument instead")
        else:
            # it is old way validator
            self.req_ext = [extensions]
            self.req_ext.extend(args)

    def validate(self, config, credentials, plugin_cls, plugin_cfg):
        clients = credentials["openstack"]["users"][0]["credential"].clients()
        extensions = clients.neutron().list_extensions()["extensions"]
        aliases = [x["alias"] for x in extensions]
        for extension in self.req_ext:
            if extension not in aliases:
                msg = ("Neutron extension %s "
                       "is not configured") % extension
                return self.fail(msg)
