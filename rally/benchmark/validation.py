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

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc

from rally.openstack.common.gettextutils import _


class ValidationResult(object):

    def __init__(self, is_valid=True, msg=None):
        self.is_valid = is_valid
        self.msg = msg


def add_validator(validator):
    def wrapper(func):
        if not getattr(func, 'validators', None):
            func.validators = []
        func.validators.append(validator)
        return func
    return wrapper


def image_exists(param_name):
    """Returns validator for image_id

    :param param_name: defines which variable should be used
                       to get image id value.
    """
    def image_exists_validator(**kwargs):
        image_id = kwargs.get(param_name)
        glanceclient = kwargs["clients"]["glance"]
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
        novaclient = kwargs["clients"]["nova"]
        try:
            novaclient.flavors.get(flavor=flavor_id)
            return ValidationResult()
        except nova_exc.NotFound:
            message = _("Flavor with id '%s' not found") % flavor_id
            return ValidationResult(False, message)
    return flavor_exists_validator
