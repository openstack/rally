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

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc

from rally.benchmark import types as types
from rally.common.i18n import _
from rally import consts
from rally import exceptions
from rally.verification.verifiers.tempest import tempest


class ValidationResult(object):

    def __init__(self, is_valid=True, msg=None):
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
        ex. @my_decorator("arg1"), then args = ('arg1',)
        :param kwargs: the keyword arguments of the decorator of the scenario
        ex. @my_decorator(kwarg1="kwarg1"), then kwargs = {"kwarg1": "kwarg1"}
        """

        @functools.wraps(fn)
        def wrap_validator(config, clients, deployment):
            # NOTE(amaretskiy): validator is successful by default
            return (fn(config, clients, deployment, *args, **kwargs) or
                    ValidationResult())

        def wrap_scenario(scenario):
            # TODO(boris-42): remove this in future.
            wrap_validator.permission = getattr(fn, "permission",
                                                consts.EndpointPermission.USER)
            if not hasattr(scenario, "validators"):
                scenario.validators = []
            scenario.validators.append(wrap_validator)
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
    :param nullable: Allow parameter not specified, or paramater=None
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
        return ValidationResult()

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
        return ValidationResult()
    except (ValueError, TypeError):
        return ValidationResult(
            False,
            "%(name)s is %(val)s which is not a valid %(type)s"
            % {"name": param_name, "val": val, "type": num_func.__name__})


@validator
def file_exists(config, clients, deployment, param_name, mode=os.R_OK):
    """Validator checks parameter is proper path to file with proper mode.

    Ensure a file exists and can be accessed with the specified mode.

    :param param_name: Name of parameter to validate
    :param mode: Access mode to test for. This should be one of:
        * os.F_OK (file exists)
        * os.R_OK (file is readable)
        * os.W_OK (file is writable)
        * os.X_OK (file is executable)

        If multiple modes are rquired they can be added, eg:
            mode=os.R_OK+os.W_OK
    """

    file_name = config.get("args", {}).get(param_name)
    if os.access(file_name, mode):
        return ValidationResult()
    else:
        return ValidationResult(
            False, "Could not open %(file_name)s with mode %(mode)s "
            "for parameter %(param_name)s"
            % {"file_name": file_name, "mode": mode, "param_name": param_name})


def _get_validated_image(config, clients, param_name):
    image_value = config.get("args", {}).get(param_name)
    if not image_value:
        msg = "Parameter %s is not specified." % param_name
        return (ValidationResult(False, msg), None)
    try:
        image_id = types.ImageResourceType.transform(
            clients=clients, resource_config=image_value)
        image = clients.glance().images.get(image=image_id)
        return (ValidationResult(), image)
    except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
        message = _("Image '%s' not found") % image_value
        return (ValidationResult(False, message), None)


def _get_validated_flavor(config, clients, param_name):
    flavor_value = config.get("args", {}).get(param_name)
    if not flavor_value:
        msg = "Parameter %s is not specified." % param_name
        return (ValidationResult(False, msg), None)
    try:
        flavor_id = types.FlavorResourceType.transform(
            clients=clients, resource_config=flavor_value)
        flavor = clients.nova().flavors.get(flavor=flavor_id)
        return (ValidationResult(), flavor)
    except (nova_exc.NotFound, exceptions.InvalidScenarioArgument):
        message = _("Flavor '%s' not found") % flavor_value
        return (ValidationResult(False, message), None)


@validator
def image_exists(config, clients, deployment, param_name):
    """Returns validator for image_id

    :param param_name: defines which variable should be used
                       to get image id value.
    """
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
                          image_name):
    """Returns validator for image could be used for current flavor

    :param flavor_name: defines which variable should be used
                       to get flavor id value.
    :param image_name: defines which variable should be used
                       to get image id value.

    """
    valid_result, flavor = _get_validated_flavor(config, clients, flavor_name)
    if not valid_result.is_valid:
        return valid_result

    valid_result, image = _get_validated_image(config, clients, image_name)
    if not valid_result.is_valid:
        return valid_result

    if flavor.ram < (image.min_ram or 0):
        message = _("The memory size for flavor '%s' is too small "
                    "for requested image '%s'") % (flavor.id, image.id)
        return ValidationResult(False, message)

    if flavor.disk:
        if (image.size or 0) > flavor.disk * (1024 ** 3):
            message = _("The disk size for flavor '%s' is too small "
                        "for requested image '%s'") % (flavor.id, image.id)
            return ValidationResult(False, message)

        if (image.min_disk or 0) > flavor.disk:
            message = _("The disk size for flavor '%s' is too small "
                        "for requested image '%s'") % (flavor.id, image.id)
            return ValidationResult(False, message)
    return ValidationResult()


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

    return ValidationResult()


@validator
def external_network_exists(config, clients, deployment, network_name,
                            use_external_network):
    """Validator checks that externatl network with network_name exist."""

    if not config.get("args", {}).get(use_external_network, True):
        return ValidationResult()

    ext_network = config.get("args", {}).get(network_name, "public")
    networks = [net.name for net in clients.nova().floating_ip_pools.list()]

    if isinstance(networks[0], dict):
        networks = [n["name"] for n in networks]

    if ext_network not in networks:
        message = _("External (floating) network with name %(network)s "
                    "not found. "
                    "Available networks: %(networks)s") % {
                        "network": ext_network,
                        "networks": networks
                    }
        return ValidationResult(False, message)

    return ValidationResult()


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
    verifier = tempest.Tempest(deployment["uuid"])
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

    if not wrong_tests:
        return ValidationResult()
    else:
        message = (_("One or more tests not found: '%s'") %
                   "', '".join(sorted(wrong_tests)))
        return ValidationResult(False, message)


@validator
def tempest_set_exists(config, clients, deployment):
    """Validator that check that tempest set_name is valid."""
    set_name = config.get("args", {}).get("set_name")

    if not set_name:
        return ValidationResult(False, "`set_name` is not specified.")

    if set_name not in consts.TEMPEST_TEST_SETS:
        message = _("There is no tempest set with name '%s'.") % set_name
        return ValidationResult(False, message)

    return ValidationResult()


@validator
def required_parameters(config, clients, deployment, *required_params):
    """Validtor for checking required parameters are specified.

    :param *required_params: list of required parameters
    """
    missing = set(required_params) - set(config.get("args", {}))
    if missing:
        message = _("%s parameters are not defined in "
                    "the benchmark config file") % ", ".join(missing)
        return ValidationResult(False, message)
    return ValidationResult()


@validator
def required_services(config, clients, deployment, *required_services):
    """Validator checks if specified OpenStack services are available.

    :param *required_services: list of services names
    """
    available_services = clients.services().values()
    for service in required_services:
        if service not in consts.Service:
            return ValidationResult(False, _("Unknown service: %s") % service)
        if service not in available_services:
            return ValidationResult(
                False, _("Service is not available: %s") % service)

    return ValidationResult()


@validator
def required_contexts(config, clients, deployment, *context_names):
    """Validator hecks if required benchmark contexts are specified.

    :param *context_names: list of context names that should be specified
    """
    missing_contexts = set(context_names) - set(config.get("context", {}))
    if missing_contexts:
        message = (_("The following contexts are required but missing from "
                     "the benchmark configuration file: %s") %
                   ", ".join(missing_contexts))
        return ValidationResult(False, message)
    else:
        return ValidationResult()


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
        return ValidationResult()

    if deployment["admin"]:
        if users and not config.get("context", {}).get("users"):
            return ValidationResult(False,
                                    _("You should specify 'users' context"))
        return ValidationResult()

    if deployment["users"] and admin:
        return ValidationResult(False, _("Admin credentials required"))

    return ValidationResult()


@validator
def volume_type_exists(config, clients, deployment, param_name):
    """Returns validator for volume types.

       check_types: defines variable to be used as the flag to determine if
                    volume types should be checked for existence.
    """
    val = config.get("args", {}).get(param_name)
    if val:
        volume_types_list = clients.cinder().volume_types.list()
        if len(volume_types_list) < 1:
            message = (_("Must have at least one volume type created "
                         "when specifying use of volume types."))
            return ValidationResult(False, message)
    return ValidationResult()
