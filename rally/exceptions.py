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


from oslo.config import cfg
import sys

from rally.openstack.common.gettextutils import _  # noqa
from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='make exception message format errors fatal'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


class RallyException(Exception):
    """Base Rally Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_('Exception in string format operation'))
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    # at least get the core message out if something happened
                    message = self.msg_fmt

        super(RallyException, self).__init__(message)

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return unicode(self)


class ImmutableException(RallyException):
    msg_fmt = _("This object is immutable.")


class InvalidArgumentsException(RallyException):
    msg_fmt = _("Invalid arguments: '%(message)s'")


class InvalidConfigException(RallyException):
    msg_fmt = _("This config is invalid: `%(message)s`")


class TestException(RallyException):
    msg_fmt = _("Test failed: %(test_message)s")


class DeploymentVerificationException(TestException):
    msg_fmt = _("Verification test failed: %(test_message)s")


class NotFoundException(RallyException):
    msg_fmt = _("Not found.")


class NoSuchEngine(NotFoundException):
    msg_fmt = _("There is no engine with name `%(engine_name)s`.")


class NoSuchVMProvider(NotFoundException):
    msg_fmt = _("There is no vm provider with name `%(vm_provider_name)s`.")


class NoSuchVerificationTest(NotFoundException):
    msg_fmt = _("No such verification test: `%(test_name)s`.")


class NoSuchScenario(NotFoundException):
    msg_fmt = _("There is no benchmark scenario with name `%(name)s`.")


class NoSuchConfigField(NotFoundException):
    msg_fmt = _("There is no field in the task config with name `%(name)s`.")


class TaskNotFound(NotFoundException):
    msg_fmt = _("Task with uuid=%(uuid)s not found.")


class DeploymentNotFound(NotFoundException):
    msg_fmt = _("Deployment with uuid=%(uuid)s not found.")


class DeploymentIsBusy(RallyException):
    msg_fmt = _("There are allocated resources for the deployment with "
                "uuid=%(uuid)s.")


class ResourceNotFound(NotFoundException):
    msg_fmt = _("Resource with id=%(id)s not found.")


class TimeoutException(RallyException):
    msg_fmt = _("Timeout exceeded.")


class GetResourceFailure(RallyException):
    msg_fmt = _("Failed to get the resource due to invalid status:"
                "`%(status)s`")


class SSHError(RallyException):
    msg_fmt = _("Remote command failed.")


class TaskInvalidStatus(RallyException):
    msg_fmt = _("Task `%(uuid)s` in `%(actual)s` status but `%(require)s` is "
                "required.")


class ChecksumMismatch(RallyException):
    msg_fmt = _("Checksum mismatch for image: %(url)s")
