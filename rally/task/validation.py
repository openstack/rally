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

from rally.common import logging
from rally.common import validation


LOG = logging.getLogger(__name__)

# TODO(astudenov): remove after deprecating all old validators
add = validation.add


class ValidationResult(object):

    def __init__(self, is_valid, msg="", etype=None, etraceback=None):
        self.is_valid = is_valid
        self.msg = msg
        self.etype = etype
        self.etraceback = etraceback

    def __str__(self):
        if self.is_valid:
            return "validation success"
        if self.etype:
            return ("---------- Exception in validator ----------\n" +
                    self.etraceback)
        return self.msg


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="old_validator", platform="openstack")
class OldValidator(validation.Validator):

    class Deployment(object):
        def __init__(self, ctx):
            self.ctx = ctx

        def get_credentials_for(self, platform):
            return {"admin": self.ctx["admin"]["credential"],
                    "users": [u["credential"] for u in self.ctx["users"]]}

    def __init__(self, fn, *args, **kwargs):
        """Legacy validator for OpenStack scenarios

        :param fn: function that performs validation
        """
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def validate(self, context, config, plugin_cls, plugin_cfg):
        users = context["users"]

        deployment = self.Deployment(context)

        if users:
            users = [user["credential"].clients() for user in users]
            for clients in users:
                result = self._run_fn(config, deployment, clients)
                if result and not result.is_valid:
                    self.fail(str(result))
            return
        else:
            result = self._run_fn(config, deployment)
            if result and not result.is_valid:
                self.fail(str(result))

    def _run_fn(self, config, deployment, clients=None):
        return self.fn(config, clients, deployment, *self.args, **self.kwargs)


def validator(fn):
    """Decorator that constructs a scenario validator from given function.

    Decorated function should return ValidationResult on error.

    :param fn: function that performs validation
    :returns: rally scenario validator
    """

    LOG.warning("The old validator mechanism is deprecated since Rally 0.10.0."
                " Use plugin base for validators - "
                "rally.common.validation.Validator (see rally.plugin.common."
                "validators and rally.plugins.openstack.validators for "
                "examples).")

    def wrap_given(*args, **kwargs):
        """Dynamic validation decorator for scenario.

        :param args: the arguments of the decorator of the scenario
        ex. @my_decorator("arg1"), then args = ("arg1",)
        :param kwargs: the keyword arguments of the decorator of the scenario
        ex. @my_decorator(kwarg1="kwarg1"), then kwargs = {"kwarg1": "kwarg1"}
        """
        def wrap_scenario(scenario):
            scenario._meta_setdefault("validators", [])
            scenario._meta_get("validators").append(
                ("old_validator", (fn, ) + args, kwargs))
            return scenario

        return wrap_scenario

    return wrap_given


# TODO(astudenov): remove deprecated validators in 1.0.0

def deprecated_validator(name, old_validator_name, rally_version):
    def decorator(*args, **kwargs):
        def wrapper(plugin):
            plugin_name = plugin.get_name()
            LOG.warning(
                "Plugin '%s' uses validator 'rally.task.validation.%s' which "
                "is deprecated in favor of '%s' (it should be used "
                "via new decorator 'rally.common.validation.add') in "
                "Rally v%s."
                % (plugin_name, old_validator_name, name, rally_version))
            plugin._meta_setdefault("validators", [])
            plugin._meta_get("validators").append((name, args, kwargs,))
            return plugin
        return wrapper
    return decorator


_deprecated_platform_validator = deprecated_validator(
    "required_platform", "required_openstack", "0.10.0")

required_openstack = functools.partial(
    _deprecated_platform_validator, platform="openstack")

number = deprecated_validator("number", "number", "0.10.0")

image_exists = deprecated_validator("image_exists", "image_exists", "0.10.0")

external_network_exists = deprecated_validator("external_network_exists",
                                               "external_network_exists",
                                               "0.10.0")

required_neutron_extensions = deprecated_validator(
    "required_neutron_extensions", "required_neutron_extensions", "0.10.0")

image_valid_on_flavor = deprecated_validator("image_valid_on_flavor",
                                             "image_valid_on_flavor",
                                             "0.10.0")

required_clients = deprecated_validator("required_clients", "required_clients",
                                        "0.10.0")

required_services = deprecated_validator("required_services",
                                         "required_services", "0.10.0")

validate_heat_template = deprecated_validator("validate_heat_template",
                                              "validate_heat_template",
                                              "0.10.0")

restricted_parameters = deprecated_validator("restricted_parameters",
                                             "restricted_parameters",
                                             "0.10.0")

required_cinder_services = deprecated_validator("required_cinder_services",
                                                "required_cinder_services",
                                                "0.10.0")

required_api_versions = deprecated_validator("required_api_versions",
                                             "required_api_versions",
                                             "0.10.0")

required_contexts = deprecated_validator("required_contexts",
                                         "required_contexts",
                                         "0.10.0")

required_param_or_context = deprecated_validator("required_param_or_context",
                                                 "required_param_or_context",
                                                 "0.10.0")

volume_type_exists = deprecated_validator("volume_type_exists",
                                          "volume_type_exists",
                                          "0.10.0")

file_exists = deprecated_validator("file_exists", "file_exists", "0.10.0")

valid_command = deprecated_validator("valid_command", "valid_command",
                                     "0.10.0")

flavor_exists = deprecated_validator("flavor_exists", "flavor_exists",
                                     "0.10.0")

_deprecated_share_proto = deprecated_validator(
    "enum", "validate_share_proto", "0.10.0")

validate_share_proto = functools.partial(
    _deprecated_share_proto,
    param_name="share_proto",
    values=["NFS", "CIFS", "GLUSTERFS", "HDFS", "CEPHFS"],
    case_insensitive=True)

_workbook_contains_workflow = deprecated_validator(
    "workbook_contains_workflow", "workbook_contains_workflow", "0.10.0")


def workbook_contains_workflow(workbook, workflow_name):
    return _workbook_contains_workflow(workbook_param=workbook,
                                       workflow_param=workflow_name)
