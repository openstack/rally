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

from rally.common import cfg
from rally.common import logging
from rally.plugins.openstack.cfg import opts as openstack_opts
from rally.task import engine

CONF = cfg.CONF


def list_opts():

    merged_opts = {"DEFAULT": []}
    for category, options in openstack_opts.list_opts().items():
        merged_opts.setdefault(category, [])
        merged_opts[category].extend(options)

    merged_opts["DEFAULT"].extend(logging.DEBUG_OPTS)
    merged_opts["DEFAULT"].extend(engine.TASK_ENGINE_OPTS)

    return merged_opts.items()


def update_opt_defaults():
    logging.oslogging.cfg.set_defaults(
        logging.oslogging._options.generic_log_opts,
        use_stderr=True
    )


_registered = False


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
