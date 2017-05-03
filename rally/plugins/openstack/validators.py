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
from novaclient import exceptions as nova_exc
from rally.task import types

from rally.common import logging
from rally.common import validation
from rally import exceptions
from rally.plugins.openstack.context.nova import flavors as flavors_ctx
from rally.plugins.openstack import types as openstack_types

LOG = logging.getLogger(__name__)
ValidationResult = validation.ValidationResult


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


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="image_valid_on_flavor", namespace="openstack")
class ImageValidOnFlavorValidator(validation.Validator):

    def __init__(self, flavor_param, image_param,
                 fail_on_404_image=True, validate_disk=True):
        """Returns validator for image could be used for current flavor

        :param flavor_param: defines which variable should be used
                           to get flavor id value.
        :param image_param: defines which variable should be used
                           to get image id value.
        :param validate_disk: flag to indicate whether to validate flavor's
                              disk. Should be True if instance is booted from
                              image. Should be False if instance is booted
                              from volume. Default value is True.
        :param fail_on_404_image: flag what indicate whether to validate image
                                  or not.
        """
        super(ImageValidOnFlavorValidator, self).__init__()
        self.flavor_name = flavor_param
        self.image_name = image_param
        self.fail_on_404_image = fail_on_404_image
        self.validate_disk = validate_disk

    def _get_validated_image(self, config, clients, param_name):
        image_context = config.get("context", {}).get("images", {})
        image_args = config.get("args", {}).get(param_name)
        image_ctx_name = image_context.get("image_name")

        if not image_args:
            msg = ("Parameter %s is not specified.") % param_name
            return (ValidationResult(False, msg), None)

        if "image_name" in image_context:
            # NOTE(rvasilets) check string is "exactly equal to" a regex
            # or image name from context equal to image name from args
            if "regex" in image_args:
                match = re.match(image_args.get("regex"), image_ctx_name)
            if image_ctx_name == image_args.get("name") or ("regex"
                                                            in image_args
                                                            and match):
                image = {
                    "size": image_context.get("min_disk", 0),
                    "min_ram": image_context.get("min_ram", 0),
                    "min_disk": image_context.get("min_disk", 0)
                }
                return (ValidationResult(True), image)
        try:
            image_id = openstack_types.GlanceImage.transform(
                clients=clients, resource_config=image_args)
            image = clients.glance().images.get(image_id)
            if hasattr(image, "to_dict"):
                # NOTE(stpierre): Glance v1 images are objects that can be
                # converted to dicts; Glance v2 images are already
                # dict-like
                image = image.to_dict()
            if not image.get("size"):
                image["size"] = 0
            if not image.get("min_ram"):
                image["min_ram"] = 0
            if not image.get("min_disk"):
                image["min_disk"] = 0
            return (ValidationResult(True), image)
        except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
            message = ("Image '%s' not found") % image_args
            return (ValidationResult(False, message), None)

    def _get_flavor_from_context(self, config, flavor_value):
        if "flavors" not in config.get("context", {}):
            raise exceptions.InvalidScenarioArgument("No flavors context")

        flavors = [flavors_ctx.FlavorConfig(**f)
                   for f in config["context"]["flavors"]]
        resource = types.obj_from_name(resource_config=flavor_value,
                                       resources=flavors, typename="flavor")
        flavor = flavors_ctx.FlavorConfig(**resource)
        flavor.id = "<context flavor: %s>" % flavor.name
        return (ValidationResult(True), flavor)

    def _get_validated_flavor(self, config, clients, param_name):
        flavor_value = config.get("args", {}).get(param_name)
        if not flavor_value:
            msg = "Parameter %s is not specified." % param_name
            return (ValidationResult(False, msg), None)
        try:
            flavor_id = openstack_types.Flavor.transform(
                clients=clients, resource_config=flavor_value)
            flavor = clients.nova().flavors.get(flavor=flavor_id)
            return (ValidationResult(True), flavor)
        except (nova_exc.NotFound, exceptions.InvalidScenarioArgument):
            try:
                return self._get_flavor_from_context(config, flavor_value)
            except exceptions.InvalidScenarioArgument:
                pass
            message = ("Flavor '%s' not found") % flavor_value
            return (ValidationResult(False, message), None)

    def validate(self, config, credentials, plugin_cls, plugin_cfg):

        flavor = None
        for user in credentials["openstack"]["users"]:
            clients = user["credential"].clients()

            if not flavor:
                valid_result, flavor = self._get_validated_flavor(
                    config, clients, self.flavor_name)
                if not valid_result.is_valid:
                    return valid_result

            valid_result, image = self._get_validated_image(
                config, clients, self.image_name)

            if not image and not self.fail_on_404_image:
                return

            if not valid_result.is_valid:
                return valid_result

            if flavor.ram < image["min_ram"]:
                message = ("The memory size for flavor '%s' is too small "
                           "for requested image '%s'") % (flavor.id,
                                                          image["id"])
                return self.fail(message)

            if flavor.disk and self.validate_disk:
                if image["size"] > flavor.disk * (1024 ** 3):
                    message = ("The disk size for flavor '%s' is too small "
                               "for requested image '%s'") % (flavor.id,
                                                              image["id"])
                    return self.fail(message)

                if image["min_disk"] > flavor.disk:
                    message = ("The minimal disk size for flavor '%s' is "
                               "too small for requested "
                               "image '%s'") % (flavor.id, image["id"])
                    return self.fail(message)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_clients", namespace="openstack")
class RequiredClientsValidator(validation.Validator):

    def __init__(self, components, *args, **kwargs):
        """Validator checks if specified OpenStack clients are available.

        :param components: list of client components names
        :param **kwargs: optional parameters:
                         admin - bool, whether to use admin clients
        """
        super(RequiredClientsValidator, self).__init__()
        if isinstance(components, (list, tuple)):
            # services argument is a list, so it is a new way of validators
            #  usage, args in this case should not be provided
            self.components = components
            if args:
                LOG.warning("Positional argument is not what "
                            "'required_clients' decorator expects. "
                            "Use `components` argument instead")
        else:
            # it is old way validator
            self.components = [components]
            self.components.extend(args)
        self.options = kwargs

    def _check_component(self, clients):
        for client_component in self.components:
            try:
                getattr(clients, client_component)()
            except ImportError:
                msg = ("Client for {0} is not installed. To install it run "
                       "`pip install python-{0}client`").format(
                    client_component)
                return validation.ValidationResult(False, msg)

    def validate(self, config, credentials, plugin_cls, plugin_cfg):
        LOG.warning("The validator 'required_clients' is deprecated since "
                    "Rally 0.10.0. If you are interested in it, please "
                    "contact Rally team via E-mail, IRC or Gitter (see "
                    "https://rally.readthedocs.io/en/latest/project_info"
                    "/index.html#where-can-i-discuss-and-propose-changes for "
                    "more details).")
        if self.options.get("admin", False):
            clients = credentials["openstack"]["admin"].clients()
            result = self._check_component(clients)
        else:
            for user in credentials["openstack"]["users"]:
                clients = user["credential"].clients()
                result = self._check_component(clients)
        if result:
            return self.fail(result.msg)
