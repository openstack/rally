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

from oslo.config import cfg

from rally.openstack.common import log as oslogging


common_cli_opts = [cfg.BoolOpt("rally-debug",
                   default=False,
                   help="Print debugging output only for Rally. "
                   "Off-site components stay quiet.")]

CONF = cfg.CONF
CONF.register_cli_opts(common_cli_opts)

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
    dbg_color = oslogging.ColorHandler.LEVEL_COLORS[logging.DEBUG]
    oslogging.ColorHandler.LEVEL_COLORS[logging.RDEBUG] = dbg_color

    oslogging.setup(product_name, version)

    if CONF.rally_debug:
        oslogging.getLogger(None).logger.setLevel(logging.RDEBUG)


def getLogger(name="unknown", version="unknown"):

    if name not in oslogging._loggers:
        oslogging._loggers[name] = RallyContextAdapter(logging.getLogger(name),
                                                       name,
                                                       version)
    return oslogging._loggers[name]


class RallyContextAdapter(oslogging.ContextAdapter):

    def debug(self, msg, *args, **kwargs):
        self.log(logging.RDEBUG, msg, *args, **kwargs)


def is_debug():
    return CONF.debug or CONF.rally_debug
