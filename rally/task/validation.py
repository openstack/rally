# Copyright 2014: Mirantis Inc.
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

import functools
import os
import re

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc
import six

from rally.common.i18n import _
from rally.common import objects
from rally import consts
from rally import exceptions
from rally import osclients
from rally.plugins.openstack.context.nova import flavors as flavors_ctx
from rally.plugins.openstack import types as openstack_types
from rally.task import types
from rally.verification.tempest import tempest

# TODO(boris-42): make the validators usable as a functions as well.
# At the moment validators can only be used as decorators.


class ValidationResult(object):

    def __init__(self, is_valid, msg=None):
        self.is_valid = is_valid
        self.msg = msg


def validator(fn):
    """Decorator that constructs a scenario validator from given function.

    Decorated function should return ValidationResult on error.

    :param fn: function that performs validation
    :returns: rally scenario validator
    """
    def wrap_given(*args, **kwargs):
        """Dynamic validation decorator for scenario.

        :param args: the arguments of the decorator of the benchmark scenario
        ex. @my_decorator("arg1"), then args = ("arg1",)
        :param kwargs: the keyword arguments of the decorator of the scenario
        ex. @my_decorator(kwarg1="kwarg1"), then kwargs = {"kwarg1": "kwarg1"}
        """
        @functools.wraps(fn)
        def wrap_validator(config, clients, deployment):
            # NOTE(amaretskiy): validator is successful by default
            return (fn(config, clients, deployment, *args, **kwargs) or
                    ValidationResult(True))

        def wrap_scenario(scenario):
            # TODO(boris-42): remove this in future.
            wrap_validator.permission = getattr(fn, "permission",
                                                consts.EndpointPermission.USER)

            scenario._meta_setdefault("validators", [])
            scenario._meta_get("validators").append(wrap_validator)
            return scenario

        return wrap_scenario

    return wrap_given


@validator
def number(config, clients, deployment, param_name, minval=None, maxval=None,
           nullable=False, integer_only=False):
    """Checks that parameter is number that pass specified condition.

    Ensure a parameter is within the range [minval, maxval]. This is a
    closed interval so the end points are included.

    :param param_name: Name of parameter to validate
    :param minval: Lower endpoint of valid interval
    :param maxval: Upper endpoint of valid interval
    :param nullable: Allow parameter not specified, or parameter=None
    :param integer_only: Only accept integers
    """

    val = config.get("args", {}).get(param_name)

    num_func = float
    if integer_only:
        # NOTE(boris-42): Force check that passed value is not float, this is
        #                 important cause int(float_numb) won't raise exception
        if type(val) == float:
            return ValidationResult(False,
                                    "%(name)s is %(val)s which hasn't int type"
                                    % {"name": param_name, "val": val})
        num_func = int

    # None may be valid if the scenario sets a sensible default.
    if nullable and val is None:
        return ValidationResult(True)

    try:
        number = num_func(val)
        if minval is not None and number < minval:
            return ValidationResult(
                False,
                "%(name)s is %(val)s which is less than the minimum "
                "(%(min)s)"
                % {"name": param_name, "val": number, "min": minval})
        if maxval is not None and number > maxval:
            return ValidationResult(
                False,
                "%(name)s is %(val)s which is greater than the maximum "
                "(%(max)s)"
                % {"name": param_name, "val": number, "max": maxval})
        return ValidationResult(True)
    except (ValueError, TypeError):
        return ValidationResult(
            False,
            "%(name)s is %(val)s which is not a valid %(type)s"
            % {"name": param_name, "val": val, "type": num_func.__name__})


def _file_access_ok(filename, mode, param_name, required=True):
    if not filename:
        return ValidationResult(not required,
                                "Parameter %s required" % param_name)
    if not os.access(os.path.expanduser(filename), mode):
        return ValidationResult(
            False, "Could not open %(filename)s with mode %(mode)s "
            "for parameter %(param_name)s"
            % {"filename": filename, "mode": mode, "param_name": param_name})
    return ValidationResult(True)


@validator
def file_exists(config, clients, deployment, param_name, mode=os.R_OK,
                required=True):
    """Validator checks parameter is proper path to file with proper mode.

    Ensure a file exists and can be accessed with the specified mode.
    Note that path to file will be expanded before access checking.

    :param param_name: Name of parameter to validate
    :param mode: Access mode to test for. This should be one of:
        * os.F_OK (file exists)
        * os.R_OK (file is readable)
        * os.W_OK (file is writable)
        * os.X_OK (file is executable)

        If multiple modes are required they can be added, eg:
            mode=os.R_OK+os.W_OK
    :param required: Boolean indicating whether this argument is required.
    """

    return _file_access_ok(config.get("args", {}).get(param_name), mode,
                           param_name, required)


def check_command_dict(command):
    """Check command-specifying dict `command', raise ValueError on error."""

    if type(command) != dict:
        raise ValueError("Command must be a dictionary")

    # NOTE(pboldin): Here we check for the values not for presence of the keys
    # due to template-driven configuration generation that can leave keys
    # defined but values empty.
    if command.get("interpreter"):
        script_file = command.get("script_file")
        if script_file:
            if "script_inline" in command:
                raise ValueError(
                    "Exactly one of script_inline or script_file with "
                    "interpreter is expected: %r" % command)
        # User tries to upload a shell? Make sure it is same as interpreter
        interpreter = command.get("interpreter")
        interpreter = (interpreter[-1]
                       if isinstance(interpreter, (tuple, list))
                       else interpreter)
        if (command.get("local_path") and
           command.get("remote_path") != interpreter):
            raise ValueError(
                "When uploading an interpreter its path should be as well"
                " specified as the `remote_path' string: %r" % command)
    elif not command.get("remote_path"):
        # No interpreter and no remote command to execute is given
        raise ValueError(
            "Supplied dict specifies no command to execute,"
            " either interpreter or remote_path is required: %r" % command)

    unexpected_keys = set(command) - set(["script_file", "script_inline",
                                          "interpreter", "remote_path",
                                          "local_path", "command_args"])
    if unexpected_keys:
        raise ValueError(
            "Unexpected command parameters: %s" % ", ".join(unexpected_keys))


@validator
def valid_command(config, clients, deployment, param_name, required=True):
    """Checks that parameter is a proper command-specifying dictionary.

    Ensure that the command dictionary is a proper command-specifying
    dictionary described in `vmtasks.VMTasks.boot_runcommand_delete' docstring.

    :param param_name: Name of parameter to validate
    :param required: Boolean indicating that the command dictionary is required
    """
    # TODO(amaretskiy): rework this validator into ResourceType, so this
    #                   will allow to validate parameters values as well

    command = config.get("args", {}).get(param_name)
    if command is None and not required:
        return ValidationResult(True)

    try:
        check_command_dict(command)
    except ValueError as e:
        return ValidationResult(False, str(e))

    for key in "script_file", "local_path":
        if command.get(key):
            return _file_access_ok(
                filename=command[key],
                mode=os.R_OK,
                param_name=param_name + "." + key,
                required=True)

    return ValidationResult(True)


def _get_validated_image(config, clients, param_name):
    image_context = config.get("context", {}).get("images", {})
    image_args = config.get("args", {}).get(param_name)
    image_ctx_name = image_context.get("image_name")

    if not image_args:
        msg = _("Parameter %s is not specified.") % param_name
        return (ValidationResult(False, msg), None)
    if "image_name" in image_context:
        # NOTE(rvasilets) check string is "exactly equal to" a regex
        # or image name from context equal to image name from args
        if "regex" in image_args:
            match = re.match(image_args.get("regex"), image_ctx_name)
        if image_ctx_name == image_args.get("name") or (
                "regex" in image_args and match):
            image = {
                "size": image_context.get("min_disk", 0),
                "min_ram": image_context.get("min_ram", 0),
                "min_disk": image_context.get("min_disk", 0)
            }
            return (ValidationResult(True), image)
    try:
        image_id = openstack_types.GlanceImage.transform(
            clients=clients, resource_config=image_args)
        image = clients.glance().images.get(image=image_id).to_dict()
        if not image.get("size"):
            image["size"] = 0
        if not image.get("min_ram"):
            image["min_ram"] = 0
        if not image.get("min_disk"):
            image["min_disk"] = 0
        return (ValidationResult(True), image)
    except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
        message = _("Image '%s' not found") % image_args
        return (ValidationResult(False, message), None)


def _get_flavor_from_context(config, flavor_value):
    if "flavors" not in config.get("context", {}):
        raise exceptions.InvalidScenarioArgument("No flavors context")

    flavors = [flavors_ctx.FlavorConfig(**f)
               for f in config["context"]["flavors"]]
    resource = types.obj_from_name(resource_config=flavor_value,
                                   resources=flavors, typename="flavor")
    flavor = flavors_ctx.FlavorConfig(**resource)
    flavor.id = "<context flavor: %s>" % flavor.name
    return (ValidationResult(True), flavor)


def _get_validated_flavor(config, clients, param_name):
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
            return _get_flavor_from_context(config, flavor_value)
        except exceptions.InvalidScenarioArgument:
            pass
        message = _("Flavor '%s' not found") % flavor_value
        return (ValidationResult(False, message), None)


@validator
def validate_share_proto(config, clients, deployment):
    """Validates value of share protocol for creation of Manila share."""
    allowed = ("NFS", "CIFS", "GLUSTERFS", "HDFS", )
    share_proto = config.get("args", {}).get("share_proto")
    if six.text_type(share_proto).upper() not in allowed:
        message = _("Share protocol '%(sp)s' is invalid, allowed values are "
                    "%(allowed)s.") % {"sp": share_proto,
                                       "allowed": "', '".join(allowed)}
        return ValidationResult(False, message)


@validator
def image_exists(config, clients, deployment, param_name, nullable=False):
    """Returns validator for image_id

    :param param_name: defines which variable should be used
                       to get image id value.
    :param nullable: defines image id param is required
    """
    image_value = config.get("args", {}).get(param_name)
    if not image_value and nullable:
        return ValidationResult(True)
    return _get_validated_image(config, clients, param_name)[0]


@validator
def flavor_exists(config, clients, deployment, param_name):
    """Returns validator for flavor

    :param param_name: defines which variable should be used
                       to get flavor id value.
    """
    return _get_validated_flavor(config, clients, param_name)[0]


@validator
def image_valid_on_flavor(config, clients, deployment, flavor_name,
                          image_name, validate_disk=True):
    """Returns validator for image could be used for current flavor

    :param flavor_name: defines which variable should be used
                       to get flavor id value.
    :param image_name: defines which variable should be used
                       to get image id value.
    :param validate_disk: flag to indicate whether to validate flavor's disk.
                          Should be True if instance is booted from image.
                          Should be False if instance is booted from volume.
                          Default value is True.

    """
    valid_result, flavor = _get_validated_flavor(config, clients, flavor_name)
    if not valid_result.is_valid:
        return valid_result

    valid_result, image = _get_validated_image(config, clients, image_name)
    if not valid_result.is_valid:
        return valid_result

    if flavor.ram < image["min_ram"]:
        message = _("The memory size for flavor '%s' is too small "
                    "for requested image '%s'") % (flavor.id, image["id"])
        return ValidationResult(False, message)

    if flavor.disk and validate_disk:
        if image["size"] > flavor.disk * (1024 ** 3):
            message = _("The disk size for flavor '%s' is too small "
                        "for requested image '%s'") % (flavor.id, image["id"])
            return ValidationResult(False, message)

        if image["min_disk"] > flavor.disk:
            message = _("The disk size for flavor '%s' is too small "
                        "for requested image '%s'") % (flavor.id, image["id"])
            return ValidationResult(False, message)


@validator
def network_exists(config, clients, deployment, network_name):
    """Validator checks that network with network_name exist."""

    network = config.get("args", {}).get(network_name, "private")

    networks = [net.label for net in
                clients.nova().networks.list()]
    if network not in networks:
        message = _("Network with name %(network)s not found. "
                    "Available networks: %(networks)s") % {
                        "network": network,
                        "networks": networks
        }
        return ValidationResult(False, message)


@validator
def external_network_exists(config, clients, deployment, network_name):
    """Validator checks that external network with given name exists."""
    ext_network = config.get("args", {}).get(network_name)
    if not ext_network:
        return ValidationResult(True)

    networks = [net.name for net in clients.nova().floating_ip_pools.list()]

    if networks and isinstance(networks[0], dict):
        networks = [n["name"] for n in networks]

    if ext_network not in networks:
        message = _("External (floating) network with name %(network)s "
                    "not found. "
                    "Available networks: %(networks)s") % {
                        "network": ext_network,
                        "networks": networks}
        return ValidationResult(False, message)


@validator
def tempest_tests_exists(config, clients, deployment):
    """Validator checks that specified test exists."""
    args = config.get("args", {})

    if "test_name" in args:
        tests = [args["test_name"]]
    else:
        tests = args.get("test_names", [])

    if not tests:
        return ValidationResult(False,
                                _("Parameter 'test_name' or 'test_names' "
                                  "should be specified."))
    verifier = tempest.Tempest(
        deployment["uuid"],
        source=config.get("context", {}).get("tempest", {}).get("source"))
    if not verifier.is_installed():
        try:
            verifier.install()
        except tempest.TempestSetupFailure as e:
            return ValidationResult(False, e)
    if not verifier.is_configured():
        verifier.generate_config_file()

    allowed_tests = verifier.discover_tests()

    for i, test in enumerate(tests):
        if not test.startswith("tempest.api."):
            tests[i] = "tempest.api." + test

    wrong_tests = set(tests) - allowed_tests

    if wrong_tests:
        message = (_("One or more tests not found: '%s'") %
                   "', '".join(sorted(wrong_tests)))
        return ValidationResult(False, message)


@validator
def tempest_set_exists(config, clients, deployment):
    """Validator that check that tempest set_name is valid."""
    set_name = config.get("args", {}).get("set_name")

    if not set_name:
        return ValidationResult(False, "`set_name` is not specified.")

    if set_name not in (list(consts.TempestTestsSets) +
                        list(consts.TempestTestsAPI)):
        message = _("There is no tempest set with name '%s'.") % set_name
        return ValidationResult(False, message)


@validator
def required_parameters(config, clients, deployment, *required_params):
    """Validator for checking required parameters are specified.

    :param *required_params: list of required parameters
    """
    missing = set(required_params) - set(config.get("args", {}))
    if missing:
        message = _("%s parameters are not defined in "
                    "the benchmark config file") % ", ".join(missing)
        return ValidationResult(False, message)


@validator
def required_services(config, clients, deployment, *required_services):
    """Validator checks if specified OpenStack services are available.

    :param *required_services: list of services names
    """
    available_services = list(clients.services().values())

    if consts.Service.NOVA_NET in required_services:
        nova = osclients.Clients(
            objects.Credential(**deployment["admin"])).nova()
        for service in nova.services.list():
            if (service.binary == consts.Service.NOVA_NET and
                    service.status == "enabled"):
                available_services.append(consts.Service.NOVA_NET)

    for service in required_services:
        # NOTE(andreykurilin): validator should ignore services configured via
        # context(a proper validation should be in context)
        service_config = config.get("context", {}).get(
            "api_versions", {}).get(service, {})
        if (service not in available_services and
                not ("service_type" in service_config or
                     "service_name" in service_config)):
            return ValidationResult(
                False, _("'{0}' service is not available. Hint: If '{0}' "
                         "service has non-default service_type, try to setup "
                         "it via 'api_versions' context.").format(service))


@validator
def required_neutron_extensions(config, clients, deployment,
                                *required_extensions):
    """Validator checks if the specified Neutron extension is available

    :param required_extensions: list of Neutron extensions
    """
    extensions = clients.neutron().list_extensions().get("extensions", [])
    aliases = map(lambda x: x["alias"], extensions)
    for extension in required_extensions:
        if extension not in aliases:
            msg = (_("Neutron extension %s is not configured") % extension)
            return ValidationResult(False, msg)


@validator
def required_cinder_services(config, clients, deployment, service_name):
    """Validator checks that specified Cinder service is available.

    It uses Cinder client with admin permissions to call 'cinder service-list'
    call

    :param service_name: Cinder service name
    """

    admin_client = osclients.Clients(
        objects.Credential(**deployment["admin"])).cinder()

    for service in admin_client.services.list():
        if (service.binary == six.text_type(service_name) and
                service.state == six.text_type("up")):
            return ValidationResult(True)

    msg = _("%s service is not available") % service_name
    return ValidationResult(False, msg)


@validator
def required_clients(config, clients, deployment, *components, **kwargs):
    """Validator checks if specified OpenStack clients are available.

    :param *components: list of client components names
    :param **kwargs: optional parameters:
                     admin - bool, whether to use admin clients
    """
    if kwargs.get("admin", False):
        clients = osclients.Clients(objects.Credential(**deployment["admin"]))

    for client_component in components:
        try:
            getattr(clients, client_component)()
        except ImportError:
            return ValidationResult(
                False,
                _("Client for %s is not installed. To install it run "
                  "`pip install -r"
                  " optional-requirements.txt`") % client_component)


@validator
def required_contexts(config, clients, deployment, *context_names):
    """Validator checks if required benchmark contexts are specified.

    :param *context_names: list of context names that should be specified
    """
    missing_contexts = set(context_names) - set(config.get("context", {}))
    if missing_contexts:
        message = (_("The following contexts are required but missing from "
                     "the benchmark configuration file: %s") %
                   ", ".join(missing_contexts))
        return ValidationResult(False, message)


@validator
def required_openstack(config, clients, deployment, admin=False, users=False):
    """Validator that requires OpenStack admin or (and) users.

    This allows us to create 4 kind of benchmarks:
    1) not OpenStack related (validator is not specified)
    2) requires OpenStack admin
    3) requires OpenStack admin + users
    4) requires OpenStack users

    :param admin: requires OpenStack admin
    :param users: requires OpenStack users
    """

    if not (admin or users):
        return ValidationResult(
            False, _("You should specify admin=True or users=True or both."))

    if deployment["admin"] and deployment["users"]:
        return ValidationResult(True)

    if deployment["admin"]:
        if users and not config.get("context", {}).get("users"):
            return ValidationResult(False,
                                    _("You should specify 'users' context"))
        return ValidationResult(True)

    if deployment["users"] and admin:
        return ValidationResult(False, _("Admin credentials required"))


@validator
def required_api_versions(config, clients, deployment, component, versions):
    """Validator checks component API versions."""
    versions = [str(v) for v in versions]
    versions_str = ", ".join(versions)
    msg = _("Task was designed to be used with %(component)s "
            "V%(version)s, but V%(found_version)s is "
            "selected.")
    if component == "keystone":
        if "2.0" not in versions and hasattr(clients.keystone(), "tenants"):
            return ValidationResult(False, msg % {"component": component,
                                                  "version": versions_str,
                                                  "found_version": "2.0"})
        if "3" not in versions and hasattr(clients.keystone(), "projects"):
            return ValidationResult(False, msg % {"component": component,
                                                  "version": versions_str,
                                                  "found_version": "3"})
    else:
        used_version = config.get("context", {}).get("api_versions", {}).get(
            component, {}).get("version",
                               getattr(clients, component).choose_version())
        if not used_version:
            return ValidationResult(
                False, _("Unable to determine the API version."))
        if str(used_version) not in versions:
            return ValidationResult(
                False, msg % {"component": component,
                              "version": versions_str,
                              "found_version": used_version})


@validator
def volume_type_exists(config, clients, deployment, param_name):
    """Returns validator for volume types.

       check_types: defines variable to be used as the flag to determine if
                    volume types should be checked for existence.
    """
    val = config.get("args", {}).get(param_name)
    if val:
        volume_types_list = clients.cinder().volume_types.list()
        if not volume_types_list:
            message = (_("Must have at least one volume type created "
                         "when specifying use of volume types."))
            return ValidationResult(False, message)


@validator
def restricted_parameters(config, clients, deployment, param_names,
                          subdict=None):
    """Validates that parameters is not set.

    :param param_names: parameter or parameters list to be validated.
    :param subdict: sub-dict of "config" to search for param_names. if
                    not defined - will search in "config"
    """
    if not isinstance(param_names, (list, tuple)):
        param_names = [param_names]

    restricted_params = []
    for param_name in param_names:
        args = config.get("args", {})
        a_dict, a_key = (args, subdict) if subdict else (config, "args")
        if param_name in a_dict.get(a_key, {}):
            restricted_params.append(param_name)
    if restricted_params:
        msg = (_("You can't specify parameters '%(params)s' in '%(a_dict)s'")
               % {"params": ", ".join(restricted_params),
                  "a_dict": subdict if subdict else "args"})
        return ValidationResult(False, msg)


@validator
def validate_heat_template(config, clients, deployment, *param_names):
    """Validates heat template.

    :param param_names: list of parameters to be validated.
    """
    if param_names is None:
        return ValidationResult(False, _(
            "validate_heat_template validator accepts non empty arguments "
            "in form of `validate_heat_template(\"foo\", \"bar\")`"))
    for param_name in param_names:
        template_path = config.get("args", {}).get(param_name)
        if not template_path:
            return ValidationResult(False, _(
                "Path to heat template is not specified. Its needed for "
                "heat template validation. Please check the content of `%s` "
                "scenario argument.") % param_name)
        template_path = os.path.expanduser(template_path)
        if not os.path.exists(template_path):
            return ValidationResult(False, _("No file found by the given path "
                                             "%s") % template_path)
        with open(template_path, "r") as f:
            try:
                clients.heat().stacks.validate(template=f.read())
            except Exception as e:
                dct = {
                    "path": template_path,
                    "msg": str(e),
                }
                msg = (_("Heat template validation failed on %(path)s. "
                         "Original error message: %(msg)s.") % dct)
                return ValidationResult(False, msg)
