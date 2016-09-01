# Copyright 2013: Mirantis Inc.
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

import six

from rally.common.i18n import _


class RallyException(Exception):
    """Base Rally Exception

    To correctly use this class, inherit from it and define
    a "msg_fmt" property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("%(message)s")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if "%(message)s" in self.msg_fmt:
            kwargs.update({"message": message})

        super(RallyException, self).__init__(self.msg_fmt % kwargs)

    def format_message(self):
        return six.text_type(self)


class ImmutableException(RallyException):
    msg_fmt = _("This object is immutable.")


class InvalidArgumentsException(RallyException):
    msg_fmt = _("Invalid arguments: '%(message)s'")


class InvalidConfigException(RallyException):
    msg_fmt = _("This config has invalid schema: `%(message)s`")


class InvalidRunnerResult(RallyException):
    msg_fmt = _("Type of result of `%(name)s` runner should be"
                " `base.ScenarioRunnerResult`. Got: `%(results_type)s`")


class InvalidTaskException(InvalidConfigException):
    msg_fmt = _("Task config is invalid: `%(message)s`")


class NotFoundScenarios(InvalidTaskException):
    msg_fmt = _("There are no benchmark scenarios with names: `%(names)s`.")


class InvalidTaskConfig(InvalidTaskException):
    msg_fmt = _("Input task is invalid!\n\n"
                "Subtask %(name)s[%(pos)s] has wrong configuration"
                "\Subtask configuration:\n%(config)s\n"
                "\nReason:\n %(reason)s")


class NotFoundException(RallyException):
    msg_fmt = _("The resource can not be found: %(message)s")


class ThreadTimeoutException(RallyException):
    msg_fmt = _("Iteration interrupted due to timeout.")


class PluginNotFound(NotFoundException):
    msg_fmt = _("There is no plugin with name: `%(name)s` in "
                "%(namespace)s namespace.")


class PluginWithSuchNameExists(RallyException):
    msg_fmt = _("Plugin with such name: %(name)s already exists in "
                "%(namespace)s namespace. It's module allocates at "
                "%(existing_path)s. You are trying to add plugin whose module "
                "allocates at %(new_path)s.")


class NoSuchConfigField(NotFoundException):
    msg_fmt = _("There is no field in the task config with name `%(name)s`.")


class NoSuchRole(NotFoundException):
    msg_fmt = _("There is no role with name `%(role)s`.")


class TaskNotFound(NotFoundException):
    msg_fmt = _("Task with uuid=%(uuid)s not found.")


class DeploymentNotFound(NotFoundException):
    msg_fmt = _("Deployment %(deployment)s not found.")


class DeploymentNameExists(RallyException):
    msg_fmt = _("Deployment name '%(deployment)s' already registered.")


class DeploymentIsBusy(RallyException):
    msg_fmt = _("There are allocated resources for the deployment with "
                "uuid=%(uuid)s.")


class RallyAssertionError(RallyException):
    msg_fmt = _("Assertion error: %(message)s")


class ResourceNotFound(NotFoundException):
    msg_fmt = _("Resource with id=%(id)s not found.")


class TimeoutException(RallyException):
    msg_fmt = _("Rally tired waiting for %(resource_type)s %(resource_name)s:"
                "%(resource_id)s to become %(desired_status)s current "
                "status %(resource_status)s")


class GetResourceFailure(RallyException):
    msg_fmt = _("Failed to get the resource %(resource)s: %(err)s")


class GetResourceNotFound(GetResourceFailure):
    msg_fmt = _("Resource %(resource)s is not found.")


class GetResourceErrorStatus(GetResourceFailure):
    msg_fmt = _("Resource %(resource)s has %(status)s status.\n"
                "Fault: %(fault)s")


class ScriptError(RallyException):
    msg_fmt = _("Script execution failed: %(message)s")


class TaskInvalidStatus(RallyException):
    msg_fmt = _("Task `%(uuid)s` in `%(actual)s` status but `%(require)s` is "
                "required.")


class ChecksumMismatch(RallyException):
    msg_fmt = _("Checksum mismatch for image: %(url)s")


class InvalidAdminException(InvalidArgumentsException):
    msg_fmt = _("user '%(username)s' doesn't have 'admin' role")


class InvalidEndpointsException(InvalidArgumentsException):
    msg_fmt = _("wrong keystone credentials specified in your endpoint"
                " properties. (HTTP 401)")


class HostUnreachableException(InvalidArgumentsException):
    msg_fmt = _("unable to establish connection to the remote host: %(url)s")


class InvalidScenarioArgument(RallyException):
    msg_fmt = _("Invalid scenario argument: '%(message)s'")


class BenchmarkSetupFailure(RallyException):
    msg_fmt = _("Unable to setup benchmark: '%(message)s'")


class ContextSetupFailure(RallyException):
    msg_fmt = _("Unable to setup context '%(ctx_name)s': '%(msg)s'")


class ValidationError(RallyException):
    msg_fmt = _("Validation error: %(message)s")


class NoNodesFound(RallyException):
    msg_fmt = _("There is no nodes matching filters: %(filters)r")


class UnknownRelease(RallyException):
    msg_fmt = _("Unknown release '%(release)s'")


class CleanUpException(RallyException):
    msg_fmt = _("Cleanup failed.")


class ImageCleanUpException(CleanUpException):
    msg_fmt = _("Image Deletion Failed")


class IncompatiblePythonVersion(RallyException):
    msg_fmt = _("Incompatible python version found '%(version)s', "
                "required '%(required_version)s'")


class WorkerNotFound(NotFoundException):
    msg_fmt = _("Worker %(worker)s could not be found")


class WorkerAlreadyRegistered(RallyException):
    msg_fmt = _("Worker %(worker)s already registered")


class SaharaClusterFailure(RallyException):
    msg_fmt = _("Sahara cluster %(name)s has failed to %(action)s. "
                "Reason: '%(reason)s'")


class LiveMigrateException(RallyException):
    msg_fmt = _("Live Migration failed: %(message)s")


class MigrateException(RallyException):
    msg_fmt = _("Migration failed: %(message)s")


class InvalidHostException(RallyException):
    msg_fmt = _("Live Migration failed: %(message)s")


class MultipleMatchesFound(RallyException):
    msg_fmt = _("Found multiple %(needle)s: %(haystack)s")

    def __init__(self, **kwargs):
        if "hint" in kwargs:
            self.msg_fmt += ". Hint: %(hint)s"
        super(MultipleMatchesFound, self).__init__(**kwargs)


class TempestConfigCreationFailure(RallyException):
    msg_fmt = _("Unable to create Tempest config file: %(message)s")


class SSHTimeout(RallyException):
    pass


class SSHError(RallyException):
    pass


class InvalidConnectionString(RallyException):
    msg_fmt = _("The connection string is not valid: %(message)s. Please "
                "check your connection string.")


class DowngradeNotSupported(RallyException):
    msg_fmt = _("Database schema downgrade is not supported.")
