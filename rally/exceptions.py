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

from rally.common.plugin import discover


_exception_map = None


class RallyException(Exception):
    """Base Rally Exception

    To correctly use this class, inherit from it and define
    a "msg_fmt" property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = "%(message)s"
    error_code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if "%(message)s" in self.msg_fmt:
            kwargs.update({"message": message})

        super(RallyException, self).__init__(self.msg_fmt % kwargs)

    def format_message(self):
        return six.text_type(self)


def find_exception(response):
    """Discover a proper exception class based on response object."""
    global _exception_map
    if _exception_map is None:
        _exception_map = dict(
            (e.error_code, e) for e in discover.itersubclasses(RallyException))
    exc_class = _exception_map.get(response.status_code, RallyException)

    error_data = response.json()["error"]
    if error_data["args"]:
        return exc_class(error_data["args"])
    return exc_class(error_data["msg"])


def make_exception(exc):
    """Check a class of exception and convert it to rally-like if needed."""
    if isinstance(exc, RallyException):
        return exc
    return RallyException(str(exc))


class InvalidArgumentsException(RallyException):
    error_code = 455
    msg_fmt = "Invalid arguments: '%(message)s'"


class InvalidConfigException(RallyException):
    error_code = 456
    msg_fmt = "This config has invalid schema: `%(message)s`"


class InvalidTaskException(InvalidConfigException):
    error_code = 457
    msg_fmt = "Task config is invalid: `%(message)s`"


class InvalidTaskConfig(InvalidTaskException):
    error_code = 458
    msg_fmt = ("Input task is invalid!\n\n"
               "Subtask %(name)s[%(pos)s] has wrong configuration"
               "\nSubtask configuration:\n%(config)s\n"
               "\nReason(s):\n %(reason)s")


class NotFoundException(RallyException):
    error_code = 404
    msg_fmt = "The resource can not be found: %(message)s"


class ThreadTimeoutException(RallyException):
    error_code = 515
    msg_fmt = "Iteration interrupted due to timeout."


class PluginNotFound(NotFoundException):
    error_code = 459
    msg_fmt = "There is no plugin `%(name)s` in %(platform)s platform."


class PluginWithSuchNameExists(RallyException):
    error_code = 516
    msg_fmt = (
        "Plugin with such name: %(name)s already exists in %(platform)s "
        "platform. It's module allocates at %(existing_path)s. You are trying "
        "to add plugin whose module allocates at %(new_path)s.")


class TaskNotFound(NotFoundException):
    error_code = 460
    msg_fmt = "Task with uuid=%(uuid)s not found."


class DeploymentNotFound(NotFoundException):
    error_code = 461
    msg_fmt = "Deployment %(deployment)s not found."


class DeploymentNameExists(RallyException):
    error_code = 462
    msg_fmt = "Deployment name '%(deployment)s' already registered."


class DeploymentNotFinishedStatus(RallyException):
    error_code = 463
    msg_fmt = "Deployment '%(name)s' (UUID=%(uuid)s) is '%(status)s'."


class DeploymentIsBusy(RallyException):
    error_code = 464
    msg_fmt = "There are allocated resources for the deployment %(uuid)s."


class RallyAssertionError(RallyException):
    msg_fmt = "Assertion error: %(message)s"


class ResourceNotFound(NotFoundException):
    error_code = 465
    msg_fmt = "Resource with id=%(id)s not found."


class TimeoutException(RallyException):
    error_code = 517
    msg_fmt = ("Rally tired waiting for %(resource_type)s %(resource_name)s:"
               "%(resource_id)s to become %(desired_status)s current "
               "status %(resource_status)s")


class GetResourceFailure(RallyException):
    error_code = 518
    msg_fmt = "Failed to get the resource %(resource)s: %(err)s"


class GetResourceNotFound(GetResourceFailure):
    error_code = 519
    msg_fmt = "Resource %(resource)s is not found."


class GetResourceErrorStatus(GetResourceFailure):
    error_code = 520
    msg_fmt = "Resource %(resource)s has %(status)s status.\n Fault: %(fault)s"


class ScriptError(RallyException):
    msg_fmt = "Script execution failed: %(message)s"


class TaskInvalidStatus(RallyException):
    error_code = 466
    msg_fmt = ("Task `%(uuid)s` in `%(actual)s` status but `%(require)s` is "
               "required.")


class InvalidAdminException(InvalidArgumentsException):
    error_code = 521
    msg_fmt = "user '%(username)s' doesn't have 'admin' role"


class AuthenticationFailed(InvalidArgumentsException):
    error_code = 401
    msg_fmt = ("Failed to authenticate to %(url)s for user '%(username)s'"
               " in project '%(project)s': %(etype)s: %(error)s")


class InvalidScenarioArgument(RallyException):
    error_code = 467
    msg_fmt = "Invalid scenario argument: '%(message)s'"


class ContextSetupFailure(RallyException):
    error_code = 524
    msg_fmt = "Unable to setup context '%(ctx_name)s': '%(msg)s'"


class ValidationError(RallyException):
    error_code = 468
    msg_fmt = "Validation error: %(message)s"


class WorkerNotFound(NotFoundException):
    error_code = 469
    msg_fmt = "Worker %(worker)s could not be found"


class WorkerAlreadyRegistered(RallyException):
    error_code = 525
    msg_fmt = "Worker %(worker)s already registered"


class MultiplePluginsFound(RallyException):
    error_code = 470

    msg_fmt = ("Multiple plugins found: %(plugins)s for name %(name)s. "
               "Use full name with platform to fix issue.")


class SSHTimeout(RallyException):
    error_code = 526
    pass


class SSHError(RallyException):
    error_code = 527
    pass


class InvalidConnectionString(RallyException):
    error_code = 471
    msg_fmt = "Invalid connection string: %(message)s."


class DowngradeNotSupported(RallyException):
    error_code = 528
    msg_fmt = "Database schema downgrade is not supported."
