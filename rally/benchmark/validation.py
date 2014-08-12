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

import os

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc

from rally.benchmark import types as types
from rally import consts
from rally.openstack.common.gettextutils import _
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
        def wrap_validator(config, clients, task):
            # NOTE(amaretskiy): validator is successful by default
            return (fn(config, clients, task, *args, **kwargs) or
                    ValidationResult())

        def wrap_scenario(scenario):
            # NOTE(amaretskiy): user permission by default
            wrap_validator.permission = getattr(
                fn, "permission", consts.EndpointPermission.USER)
            if not hasattr(scenario, "validators"):
                scenario.validators = []
            scenario.validators.append(wrap_validator)
            return scenario

        return wrap_scenario

    return wrap_given


# NOTE(amaretskiy): Deprecated by validator()
def add(validator):
    def wrapper(func):
        if not getattr(func, 'validators', None):
            func.validators = []
        # NOTE(msdubov): Call validators in user-mode by default
        #                (if not specified by @requires_permission(...)).
        if not hasattr(validator, 'permission'):
            validator.permission = consts.EndpointPermission.USER
        func.validators.append(validator)
        return func
    return wrapper


def requires_permission(permission):
    def wrapper(validator):
        validator.permission = permission
        return validator
    return wrapper


def number(param_name=None, minval=None, maxval=None, nullable=False,
           integer_only=False):
    """Number Validator

    Ensure a parameter is within the range [minval, maxval]. This is a
    closed interval so the end points are included.

    :param param_name: Name of parameter to validate
    :param minval: Lower endpoint of valid interval
    :param maxval: Upper endpoint of valid interval
    :param nullable: Allow parameter not specified, or paramater=None
    :param integer_only: Only accept integers
    """

    def number_validator(config, clients, task):

        num_func = float
        if integer_only:
            num_func = int

        val = config.get("args", {}).get(param_name)

        # None may be valid if the scenario sets a sensible default.
        if nullable and val is None:
            return ValidationResult()

        try:
            number = num_func(val)
            if minval is not None and number < minval:
                return ValidationResult(
                    False,
                    "%(name)s is %(val)s which is less than the minimum "
                    "(%(min)s)" % {'name': param_name,
                                   'val': number,
                                   'min': minval
                                   })
            if maxval is not None and number > maxval:
                return ValidationResult(
                    False,
                    "%(name)s is %(val)s which is greater than the maximum "
                    "(%(max)s)" % {'name': param_name,
                                   'val': number,
                                   'max': maxval
                                   })
            return ValidationResult()
        except (ValueError, TypeError):
            return ValidationResult(
                False,
                "%(name)s is %(val)s which is not a valid %(type)s"
                % {"name": param_name,
                   "val": val,
                   "type": num_func.__name__
                   })
    return number_validator


def file_exists(param_name, mode=os.R_OK):
    """File Validator

    Ensure a file exists and can be accessed with the specifie mode.

    :param param_name: Name of parameter to validate
    :param mode: Access mode to test for. This should be one of:
        * os.F_OK (file exists)
        * os.R_OK (file is readable)
        * os.W_OK (file is writable)
        * os.X_OK (file is executable)

        If multiple modes are rquired they can be added, eg:
            mode=os.R_OK+os.W_OK
    """

    def file_exists_validator(config, clients, task):
        file_name = config.get("args", {}).get(param_name)
        if os.access(file_name, mode):
            return ValidationResult()
        else:
            return ValidationResult(
                False, "Could not open %(file_name)s with mode %(mode)s "
                "for paramater %(param_name)s" % {'file_name': file_name,
                                                  'mode': mode,
                                                  'param_name': param_name
                                                  })
    return file_exists_validator


def image_exists(param_name):
    """Returns validator for image_id

    :param param_name: defines which variable should be used
                       to get image id value.
    """
    def image_exists_validator(config, clients, task):
        image_id = types.ImageResourceType.transform(
            clients=clients,
            resource_config=config.get("args", {}).get(param_name))
        try:
            clients.glance().images.get(image=image_id)
            return ValidationResult()
        except glance_exc.HTTPNotFound:
            message = _("Image with id '%s' not found") % image_id
            return ValidationResult(False, message)
    return image_exists_validator


def flavor_exists(param_name):
    """Returns validator for flavor

    :param param_name: defines which variable should be used
                       to get flavor id value.
    """
    def flavor_exists_validator(config, clients, task):
        flavor_id = types.FlavorResourceType.transform(
            clients=clients,
            resource_config=config.get("args", {}).get(param_name))
        try:
            clients.nova().flavors.get(flavor=flavor_id)
            return ValidationResult()
        except nova_exc.NotFound:
            message = _("Flavor with id '%s' not found") % flavor_id
            return ValidationResult(False, message)
    return flavor_exists_validator


def image_valid_on_flavor(flavor_name, image_name):
    """Returns validator for image could be used for current flavor

    :param flavor_name: defines which variable should be used
                       to get flavor id value.
    :param image_name: defines which variable should be used
                       to get image id value.

    """
    def image_valid_on_flavor_validator(config, clients, task):
        flavor_id = types.FlavorResourceType.transform(
            clients=clients,
            resource_config=config.get("args", {}).get(flavor_name))
        try:
            flavor = clients.nova().flavors.get(flavor=flavor_id)
        except nova_exc.NotFound:
            message = _("Flavor with id '%s' not found") % flavor_id
            return ValidationResult(False, message)

        image_id = types.ImageResourceType.transform(
            clients=clients,
            resource_config=config.get("args", {}).get(image_name))
        try:
            image = clients.glance().images.get(image=image_id)
        except glance_exc.HTTPNotFound:
            message = _("Image with id '%s' not found") % image_id
            return ValidationResult(False, message)

        if flavor.ram < (image.min_ram or 0):
            message = _("The memory size for flavor '%s' is too small "
                        "for requested image '%s'") % (flavor_id, image_id)
            return ValidationResult(False, message)

        if flavor.disk:
            if (image.size or 0) > flavor.disk * (1024 ** 3):
                message = _("The disk size for flavor '%s' is too small "
                            "for requested image '%s'") % (flavor_id, image_id)
                return ValidationResult(False, message)

            if (image.min_disk or 0) > flavor.disk:
                message = _("The disk size for flavor '%s' is too small "
                            "for requested image '%s'") % (flavor_id, image_id)
                return ValidationResult(False, message)
        return ValidationResult()
    return image_valid_on_flavor_validator


def network_exists(network_name):
    def network_exists_validator(config, clients, task):
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
    return network_exists_validator


def external_network_exists(network_name, use_external_network):
    def external_network_exists_validator(config, clients, task):
        if not config.get("args", {}).get(use_external_network, True):
            return ValidationResult()

        ext_network = config.get("args", {}).get(network_name, "public")

        networks = [net.name for net in
                    clients.nova().floating_ip_pools.list()]

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
    return external_network_exists_validator


def tempest_tests_exists():
    """Returns validator for tempest test."""
    def tempest_test_exists_validator(**kwargs):
        verifier = tempest.Tempest(kwargs["task"].task.deployment_uuid)
        if not verifier.is_installed():
            verifier.install()
        if not verifier.is_configured():
            verifier.generate_config_file()

        allowed_tests = verifier.discover_tests()

        if "test_name" in kwargs:
            tests = [kwargs["test_name"]]
        else:
            tests = kwargs["test_names"]

        for test in tests:
            if (not test.startswith("tempest.api.")
                    and test.split(".")[0] in consts.TEMPEST_TEST_SETS):
                tests[tests.index(test)] = "tempest.api." + test

        wrong_tests = set(tests) - allowed_tests

        if not wrong_tests:
            return ValidationResult()
        else:
            message = (_("One or more tests not found: '%s'") %
                       "', '".join(sorted(wrong_tests)))
            return ValidationResult(False, message)
    return tempest_test_exists_validator


def tempest_set_exists():
    """Returns validator for tempest set."""
    def tempest_set_exists_validator(**kwargs):
        if kwargs["set_name"] not in consts.TEMPEST_TEST_SETS:
            message = _("Set name '%s' not found.") % kwargs["set_name"]
            return ValidationResult(False, message)
        else:
            return ValidationResult()

    return tempest_set_exists_validator


def required_parameters(params):
    """Returns validator for required parameters

    :param params: list of required parameters
    """
    def required_parameters_validator(config, clients, task):
        missing = set(params) - set(config.get("args", {}))
        if missing:
            message = _("%s parameters are not defined in "
                        "the benchmark config file") % ", ".join(missing)
            return ValidationResult(False, message)
        return ValidationResult()
    return required_parameters_validator


@validator
def required_services(config, clients, task, *required_services):
    """Check if specified services are available.

    :param args: list of servives names
    """
    available_services = clients.services().values()
    for service in required_services:
        if service not in consts.Service:
            return ValidationResult(False, _("Unknown service: %s") % service)
        if service not in available_services:
            return ValidationResult(
                False, _("Service is not available: %s") % service)


@validator
def required_contexts(config, clients, task, *context_names):
    missing_contexts = set(context_names) - set(config.get("context", {}))
    if missing_contexts:
        message = (_("The following contexts are required but missing from "
                     "the benchmark configuration file: %s") %
                   ", ".join(missing_contexts))
        return ValidationResult(False, message)
