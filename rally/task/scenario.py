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

import inspect
import random

import six

from rally.common.i18n import _
from rally.common import logging
from rally.common.objects import task  # noqa
from rally.common.plugin import plugin
from rally.common import utils
from rally import consts
from rally import exceptions
from rally.task import atomic
from rally.task import functional
from rally.task.processing import charts


LOG = logging.getLogger(__name__)


def configure(name=None, namespace="default", context=None):
    """Configure scenario by setting proper meta data.

    This can also transform plain function into scenario plugin, however
    this approach is deprecated - now scenarios must be represented by classes
    based on rally.task.scenario.Scenario.

    :param name: str scenario name
    :param namespace: str plugin namespace
    :param context: default task context that is created for this scenario.
                    If there are custom user specified contexts this one
                    will be updated by provided contexts.
    """
    def wrapper(scen):
        scen.is_classbased = hasattr(scen, "run") and callable(scen.run)
        if not scen.is_classbased:
            plugin.from_func(Scenario)(scen)
        scen._meta_init()
        if name:
            if "." not in name.strip("."):
                msg = (_("Scenario name must include a dot: '%s'") % name)
                raise exceptions.RallyException(msg)
            scen._set_name_and_namespace(name, namespace)
        else:
            scen._meta_set("namespace", namespace)
        scen._meta_set("default_context", context or {})
        return scen
    return wrapper


class ConfigurePluginMeta(type):
    """Finish Scenario plugin configuration.

    After @scenario.configure() is performed to cls.method, method.im_class is
    pointing to FuncPlugin class instead of original cls. There is no way to
    fix this, mostly because im_class is add to method when it's called via
    cls, e.g. cls.method. Decorator is different case so there is no
    information about cls. method._plugin is pointing to FuncPlugin that has
    FuncPlugin pointer to method. What should be done is to set properly
    FuncPluing.func_ref to the cls.method

    This metaclass iterates over all cls methods and fix func_ref of FuncPlugin
    class so func_ref will be cls.method instead of FuncPlugin.method.

    Additionally this metaclass sets plugin names if they were not set explicit
    via configure(). Default name is <cls_name>.<method_name>

    As well we need to keep cls_ref inside of _meta because Python3 loves us.

    Viva black magic and dirty hacks.
    """
    def __init__(cls, name, bases, namespaces):

        super(ConfigurePluginMeta, cls).__init__(name, bases, namespaces)

        for name, field in six.iteritems(namespaces):
            if callable(field) and hasattr(field, "_plugin"):
                field._plugin._meta_set("cls_ref", cls)

                if not field._meta_get("name", None):
                    field._set_name_and_namespace(
                        "%s.%s" % (cls.__name__, field.__name__),
                        field.get_namespace())

                field._plugin.func_ref = getattr(
                    cls, field._plugin.func_ref.__name__)


@plugin.base()
@six.add_metaclass(ConfigurePluginMeta)
class Scenario(plugin.Plugin,
               atomic.ActionTimerMixin,
               functional.FunctionalMixin,
               utils.RandomNameGeneratorMixin):
    """This is base class for any benchmark scenario.

       You should create subclass of this class. And your test scenarios will
       be auto discoverable and you will be able to specify it in test config.
    """
    RESOURCE_NAME_FORMAT = "s_rally_XXXXXXXX_XXXXXXXX"

    def __init__(self, context=None):
        super(Scenario, self).__init__()
        self.context = context or {}
        self.task = self.context.get("task", {})
        self._idle_duration = 0.0
        self._output = {"additive": [], "complete": []}

    @staticmethod
    def _validate_helper(validators, clients, config, deployment):
        for validator in validators:
            try:
                result = validator(config, clients=clients,
                                   deployment=deployment)
            except Exception as e:
                LOG.exception(e)
                raise exceptions.InvalidScenarioArgument(e)
            else:
                if not result.is_valid:
                    raise exceptions.InvalidScenarioArgument(result.msg)

    @staticmethod
    def _validate_scenario_args(scenario, name, config):
        if scenario.is_classbased:
            # We need initialize scenario class to access instancemethods
            scenario = scenario().run
        args, _varargs, varkwargs, defaults = inspect.getargspec(scenario)

        hint_msg = (" Use `rally plugin show --name %s` to display "
                    "scenario description." % name)

        # scenario always accepts an instance of scenario cls as a first arg
        missed_args = args[1:]
        if defaults:
            # do not require args with default values
            missed_args = missed_args[:-len(defaults)]
        if "args" in config:
            missed_args = set(missed_args) - set(config["args"])
        if missed_args:
            msg = ("Argument(s) '%(args)s' should be specified in task config."
                   "%(hint)s" % {"args": "', '".join(missed_args),
                                 "hint": hint_msg})
            raise exceptions.InvalidArgumentsException(msg)

        if varkwargs is None and "args" in config:
            redundant_args = set(config["args"]) - set(args[1:])
            if redundant_args:
                msg = ("Unexpected argument(s) found ['%(args)s'].%(hint)s" %
                       {"args": "', '".join(redundant_args),
                        "hint": hint_msg})
                raise exceptions.InvalidArgumentsException(msg)

    @classmethod
    def validate(cls, name, config, admin=None, users=None, deployment=None):
        """Semantic check of benchmark arguments."""
        scenario = Scenario.get(name)

        cls._validate_scenario_args(scenario, name, config)

        validators = scenario._meta_get("validators", default=[])

        if not validators:
            return

        admin_validators = [v for v in validators
                            if v.permission == consts.EndpointPermission.ADMIN]
        user_validators = [v for v in validators
                           if v.permission == consts.EndpointPermission.USER]

        # NOTE(boris-42): Potential bug, what if we don't have "admin" client
        #                 and scenario have "admin" validators.
        if admin:
            cls._validate_helper(admin_validators, admin, config, deployment)
        if users:
            for user in users:
                cls._validate_helper(user_validators, user, config, deployment)

    def sleep_between(self, min_sleep, max_sleep, atomic_delay=0.1):
        """Call an interruptable_sleep() for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_duration
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param atomic_delay: parameter with which  time.sleep would be called
                             int(sleep_time / atomic_delay) times.
        """
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
