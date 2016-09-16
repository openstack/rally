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
import collections
import threading

import jsonschema
import six

from rally.common.i18n import _, _LE
from rally.common import logging
from rally.common import objects
from rally.common.plugin import plugin
from rally.common import utils as rutils
from rally import consts
from rally.task import trigger
from rally.task import utils


LOG = logging.getLogger(__name__)


configure = plugin.configure


class HookExecutor(object):
    """Runs hooks and collects results from them."""

    def __init__(self, config, task):
        self.config = config
        self.task = task
        self._timer_thread = threading.Thread(target=self._timer_method)
        self._timer_stop_event = threading.Event()

        # map trigers to event types
        self.triggers = collections.defaultdict(list)
        for hook in config.get("hooks", []):
            trigger_obj = trigger.Trigger.get(
                hook["trigger"]["name"])(hook["trigger"]["args"])
            trigger_event_type = trigger_obj.get_configured_event_type()
            self.triggers[trigger_event_type].append(
                (trigger_obj, hook["name"], hook["args"], hook["description"])
            )

        # list of executed hooks
        self.hooks = []

    def _timer_method(self):
        """Timer thread method.

        It generates events with type "time" to inform HookExecutor
        about how many time passed since beginning of the first iteration.
        """
        stopwatch = rutils.Stopwatch(stop_event=self._timer_stop_event)
        stopwatch.start()
        seconds_since_start = 0
        while not self._timer_stop_event.isSet():
            self.on_event(event_type="time", value=seconds_since_start)
            seconds_since_start += 1
            stopwatch.sleep(seconds_since_start)

    def _start_timer(self):
        self._timer_thread.start()

    def _stop_timer(self):
        self._timer_stop_event.set()
        if self._timer_thread.ident is not None:
            self._timer_thread.join()

    def on_event(self, event_type, value):
        """Notify about event.

        This method should be called to inform HookExecutor that
        particular event occured.
        It runs hooks configured for event.
        """
        # start timer on first iteration
        if self.triggers["time"]:
            if event_type == "iteration" and value == 1:
                self._start_timer()

        triggers = self.triggers[event_type]
        for trigger_obj, hook_name, hook_args, hook_description in triggers:
            if trigger_obj.is_runnable(value=value):
                hook = Hook.get(hook_name)(
                    config=hook_args, triggered_by={event_type: value},
                    description=hook_description)
                self.hooks.append(hook)
                hook.run_async()
                LOG.info(_("Hook %s is trigged for Task %s by %s=%s")
                         % (hook_name, self.task["uuid"], event_type, value))

    def results(self):
        """Returns list of dicts with hook results."""
        self._stop_timer()
        return [hook.result() for hook in self.hooks]


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Hook(plugin.Plugin):
    """Factory for hook classes."""

    @classmethod
    def validate(cls, config):
        hook_schema = cls.get(config["name"]).CONFIG_SCHEMA
        jsonschema.validate(config["args"], hook_schema)

        trigger.Trigger.validate(config["trigger"])

    def __init__(self, config, triggered_by, description):
        self.config = config
        self._triggered_by = triggered_by
        self._description = description
        self._thread = threading.Thread(target=self._thread_method)
        self._started_at = 0.0
        self._finished_at = 0.0
        self._result = self._format_result(status=consts.HookStatus.UNKNOWN)

    def _format_result(self, status, error=None):
        """Returns hook result dict."""
        result = {
            "hook": self.get_name(),
            "status": status,
            "description": self._description,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "triggered_by": self._triggered_by,
        }
        if error is not None:
            result["error"] = error
        return result

    def set_error(self, exception_name, description, details):
        """Set error related information to result.

        :param exception_name: name of exception as string
        :param description: short description as string
        :param details: any details as string
        """
        self._result["error"] = [exception_name, description, details]

    def set_status(self, status):
        """Set status to result."""
        self._result["status"] = status

    def set_output(self, output):
        """Set output to result.

        :param output: Diagram data in task.OUTPUT_SCHEMA format
        """
        self._result["output"] = output

    def _thread_method(self):
        # Run hook synchronously
        self.run_sync()

        try:
            self.validate_result_schema()
        except jsonschema.ValidationError as validation_error:
            LOG.error(_LE("Hook %s returned result "
                          "in wrong format.") % self.get_name())
            LOG.exception(validation_error)

            self._result = self._format_result(
                status=consts.HookStatus.VALIDATION_FAILED,
                error=utils.format_exc(validation_error),
            )

    def validate_result_schema(self):
        """Validates result format."""
        jsonschema.validate(self._result, objects.task.HOOK_RESULT_SCHEMA)

    def run_async(self):
        """Run hook asynchronously."""
        self._thread.start()

    def run_sync(self):
        """Run hook synchronously."""
        try:
            with rutils.Timer() as timer:
                self.run()
        except Exception as exc:
            LOG.error(_LE("Hook %s failed during run.") % self.get_name())
            LOG.exception(exc)
            self.set_status(consts.HookStatus.FAILED)
            self.set_error(*utils.format_exc(exc))

        self._started_at = timer.timestamp()
        self._result["started_at"] = self._started_at
        self._finished_at = timer.finish_timestamp()
        self._result["finished_at"] = self._finished_at

    @abc.abstractmethod
    def run(self):
        """Run method.

        This method should be implemented in plugin.

        Hook plugin shoud call following methods to set result:
            set_result_status - to set success/failed status
        Optionally the following methods should be colled:
            set_result_error - to indicate that there was an error
            set_result_output - to provide diarmam data
        """

    def result(self):
        """Wait and return result of hook."""
        if self._thread.ident is not None:
            # hook is stil running, wait for result
            self._thread.join()
        return self._result
