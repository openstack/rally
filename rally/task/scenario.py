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

import copy
import random

from rally.common import cfg
from rally.common import logging
from rally.common.plugin import plugin
from rally.common import utils
from rally.common import validation
from rally import exceptions
from rally.task import atomic
from rally.task import functional
from rally.task.processing import charts


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF_OPTS = [
    cfg.StrOpt(
        "scenario_resource_name_format",
        help="Template is used to generate random names of resources. X is"
             "replaced with random latter, amount of X can be adjusted")
]
CONF.register_opts(CONF_OPTS)


@logging.log_deprecated_args("Use 'platform' arg instead", "0.10.0",
                             ["namespace"], log_function=LOG.warning)
def configure(name, platform="default", namespace=None, context=None):
    """Configure scenario by setting proper meta data.

    This can also transform plain function into scenario plugin, however
    this approach is deprecated - now scenarios must be represented by classes
    based on rally.task.scenario.Scenario.

    :param name: str scenario name
    :param platform: str plugin's platform
    :param context: default task context that is created for this scenario.
                    If there are custom user specified contexts this one
                    will be updated by provided contexts.
    """
    context = context or {}
    if namespace:
        platform = namespace

    def wrapper(cls):
        # TODO(boris-42): Drop this check as soon as we refactor rally report
        if "." not in name.strip("."):
            raise exceptions.RallyException(
                "Scenario name must include a dot: '%s'" % name)

        for c in context:
            if "@" not in c:
                msg = ("Old fashion plugin configuration detected in "
                       " `%(scenario)s' scenario. Use full name for "
                       " `%(context)s' context like %(context)s@platform "
                       "where 'platform' is a name of context platform ("
                       "openstack, k8s, etc).")
                LOG.warning(msg % {"scenario": "%s@%s" % (name, platform),
                                   "context": c})

        cls = plugin.configure(name=name, platform=platform)(cls)
        cls._meta_setdefault("default_context", {})

        cls._meta_get("default_context").update(context)
        return cls

    return wrapper


@validation.add_default("args-spec")
@plugin.base()
class Scenario(plugin.Plugin,
               atomic.ActionTimerMixin,
               functional.FunctionalMixin,
               utils.RandomNameGeneratorMixin,
               validation.ValidatablePluginMixin):
    """This is base class for any scenario.

        All Scenario Plugins should be subclass of this class.
    """
    RESOURCE_NAME_FORMAT = "s_rally_XXXXXXXX_XXXXXXXX"

    @classmethod
    def _get_resource_name_format(cls):
        return (CONF.scenario_resource_name_format
                or super(Scenario, cls)._get_resource_name_format())

    def __init__(self, context=None):
        super(Scenario, self).__init__()
        self.context = context or {}
        self.task = self.context.get("task", {})
        self._idle_duration = 0.0
        self._output = {"additive": [], "complete": []}

    def get_owner_id(self):
        if "owner_id" in self.context:
            return self.context["owner_id"]
        return super(Scenario, self).get_owner_id()

    @classmethod
    def get_default_context(cls):
        return copy.deepcopy(cls._meta_get("default_context"))

    def sleep_between(self, min_sleep, max_sleep=None, atomic_delay=0.1):
        """Call an interruptable_sleep() for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_duration
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param atomic_delay: parameter with which  time.sleep would be called
                             int(sleep_time / atomic_delay) times.
        """
        if max_sleep is None:
            max_sleep = min_sleep

        if not 0 <= min_sleep <= max_sleep:
            raise exceptions.InvalidArgumentsException(
                "0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        utils.interruptable_sleep(sleep_time, atomic_delay)
        self._idle_duration += sleep_time

    def idle_duration(self):
        """Returns duration of all sleep_between."""
        return self._idle_duration

    def add_output(self, additive=None, complete=None):
        """Add iteration's custom output data.

        This saves custom output data to task results. The main way to get
        this data processed is to find it in HTML report ("Scenario Data"
        tab), where it is displayed by tables or various charts (StackedArea,
        Lines, Pie).

        Take a look at "Processing Output Charts" section of Rally Plugins
        Reference to find explanations and examples about additive and
        complete output types and how to display this output data by
        specific widgets.

        Here is a simple example how to add both additive and complete data
        and display them by StackedArea widget in HTML report:

        .. code-block:: python

            self.add_output(
                additive={"title": "Additive data in StackedArea",
                          "description": "Iterations trend for foo and bar",
                          "chart_plugin": "StackedArea",
                          "data": [["foo", 12], ["bar", 34]]},
                complete={"title": "Complete data as stacked area",
                          "description": "Data is shown as-is in StackedArea",
                          "chart_plugin": "StackedArea",
                          "data": [["foo", [[0, 5], [1, 42], [2, 15]]],
                                   ["bar", [[0, 2], [1, 1.3], [2, 5]]]],
                          "label": "Y-axis label text",
                          "axis_label": "X-axis label text"})

        :param additive: dict with additive output
        :param complete: dict with complete output
        :raises RallyException: if output has wrong format
        """
        for key, value in (("additive", additive), ("complete", complete)):
            if value:
                message = charts.validate_output(key, value)
                if message:
                    raise exceptions.RallyException(message)
                self._output[key].append(value)

    @classmethod
    def _get_doc(cls):
        return cls.run.__doc__
