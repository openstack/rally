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

import itertools

from oslo_config import cfg

from rally.common import logging
from rally import osclients
from rally.plugins.openstack.cfg import opts as openstack_opts
from rally.task import engine

CONF = cfg.CONF


def list_opts():

    merged_opts = {}
    for category, options in openstack_opts.list_opts().items():
        merged_opts.setdefault(category, [])
        merged_opts[category].extend(options)
    merged_opts["DEFAULT"] = itertools.chain(logging.DEBUG_OPTS,
                                             osclients.OSCLIENTS_OPTS,
                                             engine.TASK_ENGINE_OPTS)
    return merged_opts.items()


def register():
    for category, options in list_opts():
        group = cfg.OptGroup(name=category, title="%s options" % category)
        if category != "DEFAULT":
            CONF.register_group(group)
        CONF.register_opts(options, group=group)
