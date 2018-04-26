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

import inspect
import os
import re
import six

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc
from rally.task import types

from rally.common import logging
from rally.common import validation
from rally.common import yamlutils as yaml
from rally import consts
from rally import exceptions
from rally.plugins.common import validators
from rally.plugins.openstack.context.keystone import roles
from rally.plugins.openstack.context.nova import flavors as flavors_ctx
from rally.plugins.openstack import types as openstack_types

LOG = logging.getLogger(__name__)


def with_roles_ctx():
    """Add roles to users for validate

    """
    def decorator(func):
        def wrapper(*args, **kw):
            func_type = inspect.getcallargs(func, *args, **kw)
            config = func_type.get("config", {})
            context = func_type.get("context", {})
            if config.get("contexts", {}).get("roles") \
                    and context.get("admin", {}):
                context["config"] = config["contexts"]
                rolegenerator = roles.RoleGenerator(context)
                with rolegenerator:
                    rolegenerator.setup()
                    func(*args, **kw)
            else:
                func(*args, **kw)
        return wrapper
    return decorator


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="image_exists", platform="openstack")
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

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):

        image_args = config.get("args", {}).get(self.param_name)

        if not image_args and self.nullable:
            return

        image_context = config.get("contexts", {}).get("images", {})
        image_ctx_name = image_context.get("image_name")

        if not image_args:
            self.fail("Parameter %s is not specified." % self.param_name)

        if "image_name" in image_context:
            # NOTE(rvasilets) check string is "exactly equal to" a regex
            # or image name from context equal to image name from args
            if "regex" in image_args:
                match = re.match(image_args.get("regex"), image_ctx_name)
            if image_ctx_name == image_args.get("name") or (
                    "regex" in image_args and match):
                return
        try:
            for user in context["users"]:
                image_processor = openstack_types.GlanceImage(
                    context={"admin": {"credential": user["credential"]}})
                image_id = image_processor.pre_process(image_args, config={})
                user["credential"].clients().glance().images.get(image_id)
        except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
            self.fail("Image '%s' not found" % image_args)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="external_network_exists", platform="openstack")
class ExternalNetworkExistsValidator(validation.Validator):

    def __init__(self, param_name):
        """Validator checks that external network with given name exists.

        :param param_name: name of validated network
        """
        super(ExternalNetworkExistsValidator, self).__init__()
        self.param_name = param_name

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):

        ext_network = config.get("args", {}).get(self.param_name)
        if not ext_network:
            return

        result = []
        for user in context["users"]:
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
            self.fail("\n".join(result))


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_neutron_extensions", platform="openstack")
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

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):
        clients = context["users"][0]["credential"].clients()
        extensions = clients.neutron().list_extensions()["extensions"]
        aliases = [x["alias"] for x in extensions]
        for extension in self.req_ext:
            if extension not in aliases:
                self.fail("Neutron extension %s is not configured" % extension)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="flavor_exists", platform="openstack")
class FlavorExistsValidator(validation.Validator):

    def __init__(self, param_name):
        """Returns validator for flavor

        :param param_name: defines which variable should be used
                           to get flavor id value.
        """
        super(FlavorExistsValidator, self).__init__()

        self.param_name = param_name

    def _get_flavor_from_context(self, config, flavor_value):
        if "flavors" not in config.get("contexts", {}):
            self.fail("No flavors context")

        flavors = [flavors_ctx.FlavorConfig(**f)
                   for f in config["contexts"]["flavors"]]
        resource = types.obj_from_name(resource_config=flavor_value,
                                       resources=flavors, typename="flavor")
        flavor = flavors_ctx.FlavorConfig(**resource)
        flavor.id = "<context flavor: %s>" % flavor.name
        return flavor

    def _get_validated_flavor(self, config, clients, param_name):
        flavor_value = config.get("args", {}).get(param_name)
        if not flavor_value:
            self.fail("Parameter %s is not specified." % param_name)
        try:
            flavor_processor = openstack_types.Flavor(
                context={"admin": {"credential": clients.credential}})
            flavor_id = flavor_processor.pre_process(flavor_value, config={})
            flavor = clients.nova().flavors.get(flavor=flavor_id)
            return flavor
        except (nova_exc.NotFound, exceptions.InvalidScenarioArgument):
            try:
                return self._get_flavor_from_context(config, flavor_value)
            except validation.ValidationError:
                pass
            self.fail("Flavor '%s' not found" % flavor_value)

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):
        # flavors do not depend on user or tenant, so checking for one user
        # should be enough
        clients = context["users"][0]["credential"].clients()
        self._get_validated_flavor(config=config,
                                   clients=clients,
                                   param_name=self.param_name)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="image_valid_on_flavor", platform="openstack")
class ImageValidOnFlavorValidator(FlavorExistsValidator):

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
        super(ImageValidOnFlavorValidator, self).__init__(flavor_param)
        self.image_name = image_param
        self.fail_on_404_image = fail_on_404_image
        self.validate_disk = validate_disk

    def _get_validated_image(self, config, clients, param_name):
        image_context = config.get("contexts", {}).get("images", {})
        image_args = config.get("args", {}).get(param_name)
        image_ctx_name = image_context.get("image_name")

        if not image_args:
            self.fail("Parameter %s is not specified." % param_name)

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
                return image
        try:
            image_processor = openstack_types.GlanceImage(
                context={"admin": {"credential": clients.credential}})
            image_id = image_processor.pre_process(image_args, config={})
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
            return image
        except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
            self.fail("Image '%s' not found" % image_args)

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):

        flavor = None
        for user in context["users"]:
            clients = user["credential"].clients()

            if not flavor:
                flavor = self._get_validated_flavor(
                    config, clients, self.param_name)

            try:
                image = self._get_validated_image(config, clients,
                                                  self.image_name)
            except validation.ValidationError:
                if not self.fail_on_404_image:
                    return
                raise

            if flavor.ram < image["min_ram"]:
                self.fail("The memory size for flavor '%s' is too small "
                          "for requested image '%s'." %
                          (flavor.id, image["id"]))

            if flavor.disk and self.validate_disk:
                if flavor.disk * (1024 ** 3) < image["size"]:
                    self.fail("The disk size for flavor '%s' is too small "
                              "for requested image '%s'." %
                              (flavor.id, image["id"]))

                if flavor.disk < image["min_disk"]:
                    self.fail("The minimal disk size for flavor '%s' is "
                              "too small for requested image '%s'." %
                              (flavor.id, image["id"]))


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_clients", platform="openstack")
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
                self.fail(
                    "Client for {0} is not installed. To install it run "
                    "`pip install python-{0}client`".format(client_component))

    def validate(self, context, config, plugin_cls, plugin_cfg):
        LOG.warning("The validator 'required_clients' is deprecated since "
                    "Rally 0.10.0. If you are interested in it, please "
                    "contact Rally team via E-mail, IRC or Gitter (see "
                    "https://rally.readthedocs.io/en/latest/project_info"
                    "/index.html#where-can-i-discuss-and-propose-changes for "
                    "more details).")
        if self.options.get("admin", False):
            clients = context["admin"]["credential"].clients()
            self._check_component(clients)
        else:
            for user in context["users"]:
                clients = user["credential"].clients()
                self._check_component(clients)
                break


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_services", platform="openstack")
class RequiredServicesValidator(validation.Validator):

    def __init__(self, services, *args):
        """Validator checks if specified OpenStack services are available.

        :param services: list with names of required services
        """

        super(RequiredServicesValidator, self).__init__()
        if isinstance(services, (list, tuple)):
            # services argument is a list, so it is a new way of validators
            #  usage, args in this case should not be provided
            self.services = services
            if args:
                LOG.warning("Positional argument is not what "
                            "'required_services' decorator expects. "
                            "Use `services` argument instead")
        else:
            # it is old way validator
            self.services = [services]
            self.services.extend(args)

    def validate(self, context, config, plugin_cls, plugin_cfg):
        creds = (context.get("admin", {}).get("credential", None)
                 or context["users"][0]["credential"])

        available_services = creds.clients().services().values()
        if consts.Service.NOVA_NET in self.services:
            LOG.warning("We are sorry, but Nova-network was deprecated for "
                        "a long time and latest novaclient doesn't support "
                        "it, so we too.")

        for service in self.services:
            # NOTE(andreykurilin): validator should ignore services configured
            # via context(a proper validation should be in context)
            service_config = config.get("contexts", {}).get(
                "api_versions@openstack", {}).get(service, {})

            if (service not in available_services and
                    not ("service_type" in service_config or
                         "service_name" in service_config)):
                self.fail(
                    ("'{0}' service is not available. Hint: If '{0}' "
                     "service has non-default service_type, try to"
                     " setup it via 'api_versions'"
                     " context.").format(service))


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="validate_heat_template", platform="openstack")
class ValidateHeatTemplateValidator(validation.Validator):

    def __init__(self, params, *args):
        """Validates heat template.

        :param params: list of parameters to be validated.
        """
        super(ValidateHeatTemplateValidator, self).__init__()
        if isinstance(params, (list, tuple)):
            # services argument is a list, so it is a new way of validators
            #  usage, args in this case should not be provided
            self.params = params
            if args:
                LOG.warning("Positional argument is not what "
                            "'validate_heat_template' decorator expects. "
                            "Use `params` argument instead")
        else:
            # it is old way validator
            self.params = [params]
            self.params.extend(args)

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):

        for param_name in self.params:
            template_path = config.get("args", {}).get(param_name)
            if not template_path:
                msg = ("Path to heat template is not specified. Its needed "
                       "for heat template validation. Please check the "
                       "content of `{}` scenario argument.")

                return self.fail(msg.format(param_name))
            template_path = os.path.expanduser(template_path)
            if not os.path.exists(template_path):
                self.fail("No file found by the given path %s" % template_path)
            with open(template_path, "r") as f:
                try:
                    for user in context["users"]:
                        clients = user["credential"].clients()
                        clients.heat().stacks.validate(template=f.read())
                except Exception as e:
                    self.fail("Heat template validation failed on %(path)s. "
                              "Original error message: %(msg)s." %
                              {"path": template_path, "msg": str(e)})


@validation.add("required_platform", platform="openstack", admin=True)
@validation.configure(name="required_cinder_services", platform="openstack")
class RequiredCinderServicesValidator(validation.Validator):

    def __init__(self, services):
        """Validator checks that specified Cinder service is available.

        It uses Cinder client with admin permissions to call
        'cinder service-list' call

        :param services: Cinder service name
        """
        super(RequiredCinderServicesValidator, self).__init__()
        self.services = services

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):

        clients = context["admin"]["credential"].clients()
        for service in clients.cinder().services.list():
            if (service.binary == six.text_type(self.services)
                    and service.state == six.text_type("up")):
                return

        self.fail("%s service is not available" % self.services)


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="required_api_versions", platform="openstack")
class RequiredAPIVersionsValidator(validation.Validator):

    def __init__(self, component, versions):
        """Validator checks component API versions.

        :param component: name of required component
        :param versions: version of required component
        """
        super(RequiredAPIVersionsValidator, self).__init__()
        self.component = component
        self.versions = versions

    def validate(self, context, config, plugin_cls, plugin_cfg):
        versions = [str(v) for v in self.versions]
        versions_str = ", ".join(versions)
        msg = ("Task was designed to be used with %(component)s "
               "V%(version)s, but V%(found_version)s is "
               "selected.")
        for user in context["users"]:
            clients = user["credential"].clients()
            if self.component == "keystone":
                if "2.0" not in versions and hasattr(
                        clients.keystone(), "tenants"):
                    self.fail(msg % {"component": self.component,
                                     "version": versions_str,
                                     "found_version": "2.0"})
                if "3" not in versions and hasattr(
                        clients.keystone(), "projects"):
                    self.fail(msg % {"component": self.component,
                                     "version": versions_str,
                                     "found_version": "3"})
            else:
                av_ctx = config.get("contexts", {}).get(
                    "api_versions@openstack", {})
                default_version = getattr(clients,
                                          self.component).choose_version()
                used_version = av_ctx.get(self.component, {}).get(
                    "version", default_version)
                if not used_version:
                    self.fail("Unable to determine the API version.")
                if str(used_version) not in versions:
                    self.fail(msg % {"component": self.component,
                                     "version": versions_str,
                                     "found_version": used_version})


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="volume_type_exists", platform="openstack")
class VolumeTypeExistsValidator(validation.Validator):

    def __init__(self, param_name, nullable=True):
        """Returns validator for volume types.

        :param param_name: defines variable to be used as the flag to
                           determine if volume types should be checked for
                           existence.
        :param nullable: defines volume_type param is required
        """
        super(VolumeTypeExistsValidator, self).__init__()
        self.param = param_name
        self.nullable = nullable

    @with_roles_ctx()
    def validate(self, context, config, plugin_cls, plugin_cfg):
        volume_type = config.get("args", {}).get(self.param, False)

        if not volume_type:
            if self.nullable:
                return

            self.fail("The parameter '%s' is required and should not be empty."
                      % self.param)

        for user in context["users"]:
            clients = user["credential"].clients()
            vt_names = [vt.name for vt in
                        clients.cinder().volume_types.list()]
            ctx = config.get("contexts", {}).get("volume_types", [])
            vt_names += ctx
            if volume_type not in vt_names:
                self.fail("Specified volume type %s not found for user %s."
                          " List of available types: %s" %
                          (volume_type, user, vt_names))


@validation.configure(name="workbook_contains_workflow", platform="openstack")
class WorkbookContainsWorkflowValidator(validators.FileExistsValidator):

    def __init__(self, workbook_param, workflow_param):
        """Validate that workflow exist in workbook when workflow is passed

        :param workbook_param: parameter containing the workbook definition
        :param workflow_param: parameter containing the workflow name
        """
        super(WorkbookContainsWorkflowValidator, self).__init__(workflow_param)
        self.workbook = workbook_param
        self.workflow = workflow_param

    def validate(self, context, config, plugin_cls, plugin_cfg):
        wf_name = config.get("args", {}).get(self.workflow)
        if wf_name:
            wb_path = config.get("args", {}).get(self.workbook)
            wb_path = os.path.expanduser(wb_path)
            self._file_access_ok(wb_path, mode=os.R_OK,
                                 param_name=self.workbook)

            with open(wb_path, "r") as wb_def:
                wb_def = yaml.safe_load(wb_def)
                if wf_name not in wb_def["workflows"]:
                    self.fail("workflow '%s' not found in the definition '%s'"
                              % (wf_name, wb_def))
