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

from oslo_config import cfg
from oslo_log import handlers
from oslo_log import log as oslogging

from rally.common.i18n import _

log = __import__("logging")

DEBUG_OPTS = [cfg.BoolOpt(
    "rally-debug",
    default=False,
    help="Print debugging output only for Rally. "
         "Off-site components stay quiet.")]

CONF = cfg.CONF
CONF.register_cli_opts(DEBUG_OPTS)
oslogging.register_options(CONF)

log.RDEBUG = log.DEBUG + 1
log.addLevelName(log.RDEBUG, "RALLYDEBUG")

CRITICAL = log.CRITICAL
DEBUG = log.DEBUG
ERROR = log.ERROR
FATAL = log.FATAL
INFO = log.INFO
NOTSET = log.NOTSET
RDEBUG = log.RDEBUG
WARN = log.WARN
WARNING = log.WARNING


def setup(product_name, version="unknown"):
    dbg_color = handlers.ColorHandler.LEVEL_COLORS[log.DEBUG]
    handlers.ColorHandler.LEVEL_COLORS[log.RDEBUG] = dbg_color

    oslogging.setup(CONF, product_name, version)

    if CONF.rally_debug:
        oslogging.getLogger(
            project=product_name).logger.setLevel(log.RDEBUG)


class RallyContextAdapter(oslogging.KeywordArgumentAdapter):

    def debug(self, msg, *args, **kwargs):
        self.log(log.RDEBUG, msg, *args, **kwargs)


def getLogger(name="unknown", version="unknown"):

    if name not in oslogging._loggers:
        oslogging._loggers[name] = RallyContextAdapter(log.getLogger(name),
                                                       {"project": "rally",
                                                        "version": version})
    return oslogging._loggers[name]


LOG = getLogger(__name__)


class ExceptionLogger(object):
    """Context that intercepts and logs exceptions.

    Usage::
        LOG = logging.getLogger(__name__)
        ...

        def foobar():
            with ExceptionLogger(LOG, "foobar warning") as e:
                return house_of_raising_exception()

            if e.exception:
                raise e.exception # remove if not required
    """

    def __init__(self, logger, warn=None):
        self.logger = logger
        self.warn = warn
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        if value:
            self.exception = value

            if self.warn:
                self.logger.warning(self.warn)
            self.logger.debug(value)
            if is_debug():
                self.logger.exception(value)
            return True


class CatcherHandler(log.handlers.BufferingHandler):
    def __init__(self):
        log.handlers.BufferingHandler.__init__(self, 0)

    def shouldFlush(self):
        return False

    def emit(self, record):
        self.buffer.append(record)


class LogCatcher(object):
    """Context manager that catches log messages.

    User can make an assertion on their content or fetch them all.

    Usage::
        LOG = logging.getLogger(__name__)
        ...

        def foobar():
            with LogCatcher(LOG) as catcher_in_rye:
                LOG.warning("Running Kids")

            catcher_in_rye.assertInLogs("Running Kids")
    """
    def __init__(self, logger):
        self.logger = getattr(logger, "logger", logger)
        self.handler = CatcherHandler()

    def __enter__(self):
        self.logger.addHandler(self.handler)
        return self

    def __exit__(self, type_, value, traceback):
        self.logger.removeHandler(self.handler)

    def assertInLogs(self, msg):
        """Assert that `msg' is a substring at least of one logged message.

        :param msg: Substring to look for.
        :return: Log messages where the `msg' was found.
            Raises AssertionError if none.
        """
        in_logs = [record.msg
                   for record in self.handler.buffer if msg in record.msg]
        if not in_logs:
            raise AssertionError("Expected `%s' is not in logs" % msg)
        return in_logs

    def fetchLogRecords(self):
        """Returns all logged Records."""
        return self.handler.buffer

    def fetchLogs(self):
        """Returns all logged messages."""
        return [record.msg for record in self.handler.buffer]


def _log_wrapper(obj, log_function, msg, **kw):
    """A logging wrapper for any method of a class.

    Class instances that use this decorator should have self.task or
    self.deployment attribute. The wrapper produces logs messages both
    before and after the method execution, in the following format
    (example for tasks):

    "Task <Task UUID> | Starting:  <Logging message>"
    [Method execution...]
    "Task <Task UUID> | Completed: <Logging message>"

    :param obj: task or deployment which must be attribute of "self"
    :param log_function: Logging method to be used, e.g. LOG.info
    :param msg: Text message (possibly parameterized) to be put to the log
    :param **kw: Parameters for msg
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            params = {"msg": msg % kw, "obj_name": obj.title(),
                      "uuid": getattr(self, obj)["uuid"]}
            log_function(_("%(obj_name)s %(uuid)s | Starting:  %(msg)s") %
                         params)
            result = f(self, *args, **kwargs)
            log_function(_("%(obj_name)s %(uuid)s | Completed: %(msg)s") %
                         params)
            return result
        return wrapper
    return decorator


def log_task_wrapper(log_function, msg, **kw):
    return _log_wrapper("task", log_function, msg, **kw)


def log_deploy_wrapper(log_function, msg, **kw):
    return _log_wrapper("deployment", log_function, msg, **kw)


def log_verification_wrapper(log_function, msg, **kw):
    return _log_wrapper("verification", log_function, msg, **kw)


def log_deprecated(message, rally_version, log_function=None, once=False):
    """A wrapper marking a certain method as deprecated.

    :param message: Message that describes why the method was deprecated
    :param rally_version: version of Rally when the method was deprecated
    :param log_function: Logging method to be used, e.g. LOG.info
    :param once: Show only once (default is each)
    """
    log_function = log_function or LOG.warning

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if (not once) or (not getattr(f, "_warned_dep_method", False)):
                log_function("'%(func)s' is deprecated in Rally v%(version)s: "
                             "%(msg)s" % {"msg": message,
                                          "version": rally_version,
                                          "func": f.__name__})
                setattr(f, "_warned_dep_method", once)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_deprecated_args(message, rally_version, deprecated_args,
                        log_function=None, once=False):
    """A wrapper marking certain arguments as deprecated.

    :param message: Message that describes why the arguments were deprecated
    :param rally_version: version of Rally when the arguments were deprecated
    :param deprecated_args: List of deprecated args.
    :param log_function: Logging method to be used, e.g. LOG.info
    :param once: Show only once (default is each)
    """
    log_function = log_function or LOG.warning

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if (not once) or (not getattr(f, "_warned_dep_args", False)):
                deprecated = ", ".join([
                    "`%s'" % x for x in deprecated_args if x in kwargs])
                if deprecated:
                    log_function(
                        "%(msg)s (args %(args)s deprecated in Rally "
                        "v%(version)s)" %
                        {"msg": message, "version": rally_version,
                         "args": deprecated})
                    setattr(f, "_warned_dep_args", once)
            result = f(*args, **kwargs)
            return result
        return wrapper
    return decorator


def is_debug():
    return CONF.debug or CONF.rally_debug
