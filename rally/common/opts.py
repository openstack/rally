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

import importlib

from rally.common import cfg
from rally.common import logging
from rally.task import engine

CONF = cfg.CONF


def list_opts():

    merged_opts = {"DEFAULT": []}
    merged_opts["DEFAULT"].extend(logging.DEBUG_OPTS)
    merged_opts["DEFAULT"].extend(engine.TASK_ENGINE_OPTS)

    return merged_opts.items()


def update_opt_defaults():
    logging.oslogging.cfg.set_defaults(
        logging.oslogging._options.generic_log_opts,
        use_stderr=True
    )


_registered = False
_registered_paths = []


def register_options_from_path(path):
    global _registered_paths
    if path not in _registered_paths:
        if ":" not in path:
            return
        module_name, function_name = path.split(":", 1)
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return
        list_func = getattr(module, function_name, None)
        if list_func is None:
            return

        options = list_func()
        register_opts(options.items())
        _registered_paths.append(path)


def register_opts(opts):
    for category, options in opts:
        group = cfg.OptGroup(name=category, title="%s options" % category)
        if category != "DEFAULT":
            CONF.register_group(group)
            CONF.register_opts(options, group=group)
        else:
            CONF.register_opts(options)


def register():
    global _registered

    if not _registered:
        register_opts(list_opts())

        _registered = True
