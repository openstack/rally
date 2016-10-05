# Copyright 2016: Mirantis Inc.
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

import abc

import jsonschema
import six

from rally.common.i18n import _
from rally.common import logging
from rally.common.plugin import plugin

configure = plugin.configure

LOG = logging.getLogger(__name__)


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Trigger(plugin.Plugin):
    """Factory for trigger classes."""

    CONFIG_SCHEMA = {}

    def __init__(self, context, task, hook_cls):
        self.context = context
        self.config = self.context["trigger"]["args"]
        self.task = task
        self.hook_cls = hook_cls
        self._runs = []

    @classmethod
    def validate(cls, config):
        jsonschema.validate(config["args"], cls.CONFIG_SCHEMA)

    @abc.abstractmethod
    def get_listening_event(self):
        """Returns event type to listen."""

    def on_event(self, event_type, value=None):
        """Launch hook on specified event."""
        LOG.info(_("Hook %s is triggered for Task %s by %s=%s")
                 % (self.hook_cls.__name__, self.task["uuid"],
                    event_type, value))
        hook = self.hook_cls(self.task, self.context.get("args", {}),
                             {"event_type": event_type, "value": value})
        hook.run_async()
        self._runs.append(hook)

    def get_results(self):
        results = {"config": self.context,
                   "results": [],
                   "summary": {}}
        for hook in self._runs:
            hook_result = hook.result()
            results["results"].append(hook_result)
            results["summary"].setdefault(hook_result["status"], 0)
            results["summary"][hook_result["status"]] += 1
        return results
