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

from rally import consts
from rally.openstack.common.gettextutils import _
from rally.verification.verifiers.tempest import tempest


class ValidationResult(object):

    def __init__(self, is_valid=True, msg=None):
        self.is_valid = is_valid
        self.msg = msg


def add_validator(validator):
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

    def number_validator(**kwargs):

        num_func = float
        if integer_only:
            num_func = int

        val = kwargs.get(param_name, None)

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

    def file_exists_validator(**kwargs):
        file_name = kwargs.get(param_name)
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
    def image_exists_validator(**kwargs):
        image_id = kwargs.get(param_name)
        glanceclient = kwargs["clients"].glance()
        try:
            glanceclient.images.get(image=image_id)
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
    def flavor_exists_validator(**kwargs):
        flavor_id = kwargs.get(param_name)
        novaclient = kwargs["clients"].nova()
        try:
            novaclient.flavors.get(flavor=flavor_id)
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
    def image_valid_on_flavor_validator(**kwargs):
        flavor_id = kwargs.get(flavor_name)
        novaclient = kwargs["clients"].nova()

        try:
            flavor = novaclient.flavors.get(flavor=flavor_id)
        except nova_exc.NotFound:
            message = _("Flavor with id '%s' not found") % flavor_id
            return ValidationResult(False, message)

        image_id = kwargs.get(image_name)
        glanceclient = kwargs["clients"].glance()

        try:
            image = glanceclient.images.get(image=image_id)
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


def tempest_tests_exists():
    """Returns validator for tempest test."""
    def tempest_test_exists_validator(**kwargs):
        verifier = tempest.Tempest(kwargs['task'].task.deployment_uuid)
        if not verifier.is_installed():
            verifier.install()
        if not verifier.is_configured():
            verifier.generate_config_file()

        allowed_tests = verifier.discover_tests()

        if 'test_name' in kwargs:
            tests = [kwargs['test_name']]
        else:
            tests = kwargs['test_names']

        for test in tests:
            if (not test.startswith("tempest.api.")
                    and test.split('.')[0] in consts.TEMPEST_TEST_SETS):
                tests[tests.index(test)] = 'tempest.api.' + test

        wrong_tests = set(tests) - set(allowed_tests)

        if not wrong_tests:
            return ValidationResult()
        else:
            message = (_("One or more tests not found: '%s'") %
                       "', '".join(wrong_tests))
            return ValidationResult(False, message)
    return tempest_test_exists_validator


def required_parameters(params):
    """Returns validator for required parameters

    :param params: list of required parameters
    """
    def required_parameters_validator(**kwargs):
        missing = set(params) - set(kwargs)
        if missing:
            message = _("%s parameters are not defined in "
                        "the benchmark config file") % ", ".join(missing)
            return ValidationResult(False, message)
        return ValidationResult()
    return required_parameters_validator
