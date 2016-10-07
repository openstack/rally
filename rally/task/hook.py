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
from rally.common.plugin import plugin
from rally.common import utils as rutils
from rally import consts
from rally import exceptions
from rally.task.processing import charts
from rally.task import trigger
from rally.task import utils


LOG = logging.getLogger(__name__)


configure = plugin.configure


class HookExecutor(object):
    """Runs hooks and collects results from them."""

    def __init__(self, config, task):
        self.config = config
        self.task = task

        self.triggers = collections.defaultdict(list)
        for hook in config.get("hooks", []):
            hook_cls = Hook.get(hook["name"])
            trigger_obj = trigger.Trigger.get(
                hook["trigger"]["name"])(hook, self.task, hook_cls)
            event_type = trigger_obj.get_listening_event()
            self.triggers[event_type].append(trigger_obj)

        if "time" in self.triggers:
            self._timer_thread = threading.Thread(target=self._timer_method)
            self._timer_stop_event = threading.Event()

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
        particular event occurred.
        It runs hooks configured for event.
        """
        if "time" in self.triggers:
            # start timer on first iteration
            if event_type == "iteration" and value == 1:
                self._start_timer()

        for trigger_obj in self.triggers[event_type]:
            started = trigger_obj.on_event(event_type, value)
            if started:
                LOG.info(_("Hook %s is trigged for Task %s by %s=%s")
                         % (trigger_obj.hook_cls.__name__, self.task["uuid"],
                            event_type, value))

    def results(self):
        """Returns list of dicts with hook results."""
        if "time" in self.triggers:
            self._stop_timer()
        results = []
        for triggers_group in self.triggers.values():
            for trigger_obj in triggers_group:
                results.append(trigger_obj.get_results())
        return results


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Hook(plugin.Plugin):
    """Factory for hook classes."""

    CONFIG_SCHEMA = {}

    def __init__(self, task, config, triggered_by):
        self.task = task
        self.config = config
        self._triggered_by = triggered_by
        self._thread = threading.Thread(target=self._thread_method)
        self._started_at = 0.0
        self._finished_at = 0.0
        self._result = {
            "status": consts.HookStatus.SUCCESS,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "triggered_by": self._triggered_by,
        }

    @classmethod
    def validate(cls, config):
        jsonschema.validate(config["args"], cls.CONFIG_SCHEMA)

        trigger.Trigger.validate(config["trigger"])

    def _thread_method(self):
        # Run hook synchronously
        self.run_sync()

    def set_error(self, exception_name, description, details):
        """Set error related information to result.

        :param exception_name: name of exception as string
        :param description: short description as string
        :param details: any details as string
        """
        self.set_status(consts.HookStatus.FAILED)
        self._result["error"] = {"etype": exception_name,
                                 "msg": description, "details": details}

    def set_status(self, status):
        """Set status to result."""
        self._result["status"] = status

    def add_output(self, additive=None, complete=None):
        """Save custom output.

        :param additive: dict with additive output
        :param complete: dict with complete output
        :raises RallyException: if output has wrong format
        """
        if "output" not in self._result:
            self._result["output"] = {"additive": [], "complete": []}
        for key, value in (("additive", additive), ("complete", complete)):
            if value:
                message = charts.validate_output(key, value)
                if message:
                    raise exceptions.RallyException(message)
                self._result["output"][key].append(value)

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
            self.set_error(*utils.format_exc(exc))

        self._started_at = timer.timestamp()
        self._result["started_at"] = self._started_at
        self._finished_at = timer.finish_timestamp()
        self._result["finished_at"] = self._finished_at

    @abc.abstractmethod
    def run(self):
        """Run method.

        This method should be implemented in plugin.

        Hook plugin should call following methods to set result:
            set_status - to set hook execution status
        Optionally the following methods should be called:
            set_error - to indicate that there was an error;
                        automatically sets hook execution status to 'failed'
            add_output - provide data for report
        """

    def result(self):
        """Wait and return result of hook."""
        if self._thread.ident is not None:
            # hook is still running, wait for result
            self._thread.join()
        return self._result
