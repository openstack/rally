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

import logging

from oslo_config import cfg
from oslo_log import handlers
from oslo_log import log as oslogging


DEBUG_OPTS = [cfg.BoolOpt(
    "rally-debug",
    default=False,
    help="Print debugging output only for Rally. "
         "Off-site components stay quiet.")]

CONF = cfg.CONF
CONF.register_cli_opts(DEBUG_OPTS)
oslogging.register_options(CONF)

logging.RDEBUG = logging.DEBUG + 1
logging.addLevelName(logging.RDEBUG, "RALLYDEBUG")

CRITICAL = logging.CRITICAL
DEBUG = logging.DEBUG
ERROR = logging.ERROR
FATAL = logging.FATAL
INFO = logging.INFO
NOTSET = logging.NOTSET
RDEBUG = logging.RDEBUG
WARN = logging.WARN
WARNING = logging.WARNING


def setup(product_name, version="unknown"):
    dbg_color = handlers.ColorHandler.LEVEL_COLORS[logging.DEBUG]
    handlers.ColorHandler.LEVEL_COLORS[logging.RDEBUG] = dbg_color

    oslogging.setup(CONF, product_name, version)

    if CONF.rally_debug:
        oslogging.getLogger(
            project=product_name).logger.setLevel(logging.RDEBUG)


def getLogger(name="unknown", version="unknown"):

    if name not in oslogging._loggers:
        oslogging._loggers[name] = RallyContextAdapter(logging.getLogger(name),
                                                       {"project": "rally",
                                                        "version": version})
    return oslogging._loggers[name]


class RallyContextAdapter(oslogging.KeywordArgumentAdapter):

    def debug(self, msg, *args, **kwargs):
        self.log(logging.RDEBUG, msg, *args, **kwargs)


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


class CatcherHandler(logging.handlers.BufferingHandler):
    def __init__(self):
        logging.handlers.BufferingHandler.__init__(self, 0)

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


def is_debug():
    return CONF.debug or CONF.rally_debug
