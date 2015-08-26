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

import functools
import random
import time

import six

from rally.common import costilius
from rally.common import log as logging
from rally.common.plugin import plugin
from rally.common import utils
from rally import consts
from rally import exceptions
from rally.task import functional


LOG = logging.getLogger(__name__)


def configure(name=None, namespace="default", context=None):
    """Make from plain python method task scenario plugin.

       :param name: Plugin name
       :param namespace: Plugin namespace
       :param context: Default task context that is created for this scenario.
                       If there are custom user specified contexts this one
                       will be updated by provided contexts.
    """
    def wrapper(func):
        plugin.from_func(Scenario)(func)
        func._meta_init()
        if name:
            func._set_name_and_namespace(name, namespace)
        else:
            func._meta_set("namespace", namespace)
        func._meta_set("default_context", context or {})
        return func
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


@six.add_metaclass(ConfigurePluginMeta)
class Scenario(plugin.Plugin, functional.FunctionalMixin):
    """This is base class for any benchmark scenario.

       You should create subclass of this class. And your test scenarios will
       be auto discoverable and you will be able to specify it in test config.
    """
    RESOURCE_NAME_PREFIX = "rally_"
    RESOURCE_NAME_LENGTH = 10

    def __init__(self, context=None):
        self.context = context
        self._idle_duration = 0
        self._atomic_actions = costilius.OrderedDict()

    # TODO(amaretskiy): consider about prefix part of benchmark uuid
    @classmethod
    def _generate_random_name(cls, prefix=None, length=None):
        prefix = cls.RESOURCE_NAME_PREFIX if prefix is None else prefix
        length = length or cls.RESOURCE_NAME_LENGTH
        return utils.generate_random_name(prefix, length)

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

    @classmethod
    def validate(cls, name, config, admin=None, users=None, deployment=None):
        """Semantic check of benchmark arguments."""
        validators = Scenario.get(name)._meta_get("validators", default=[])

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

    def sleep_between(self, min_sleep, max_sleep):
        """Performs a time.sleep() call for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_duration
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        """
        if not 0 <= min_sleep <= max_sleep:
            raise exceptions.InvalidArgumentsException(
                "0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)
        self._idle_duration += sleep_time

    def idle_duration(self):
        """Returns duration of all sleep_between."""
        return self._idle_duration

    def _register_atomic_action(self, name):
        """Registers an atomic action by its name."""
        self._atomic_actions[name] = None

    def _atomic_action_registered(self, name):
        """Checks whether an atomic action has been already registered."""
        return name in self._atomic_actions

    def _add_atomic_actions(self, name, duration):
        """Adds the duration of an atomic action by its name."""
        self._atomic_actions[name] = duration

    def atomic_actions(self):
        """Returns the content of each atomic action."""
        return self._atomic_actions


def atomic_action_timer(name):
    """Provide measure of execution time.

    Decorates methods of the Scenario class.
    This provides duration in seconds of each atomic action.
    """
    def wrap(func):
        @functools.wraps(func)
        def func_atomic_actions(self, *args, **kwargs):
            with AtomicAction(self, name):
                f = func(self, *args, **kwargs)
            return f
        return func_atomic_actions
    return wrap


class AtomicAction(utils.Timer):
    """A class to measure the duration of atomic operations

    This would simplify the way measure atomic operation duration
    in certain cases. For example if we want to get the duration
    for each operation which runs in an iteration
    for i in range(repetitions):
        with scenario_utils.AtomicAction(instance_of_base_scenario_subclass,
                                         "name_of_action"):
            self.clients(<client>).<operation>
    """

    def __init__(self, scenario_instance, name):
        """Create a new instance of the AtomicAction.

        :param scenario_instance: instance of subclass of base scenario
        :param name: name of the ActionBuilder
        """
        super(AtomicAction, self).__init__()
        self.scenario_instance = scenario_instance
        self.name = self._get_atomic_action_name(name)
        self.scenario_instance._register_atomic_action(self.name)

    def _get_atomic_action_name(self, name):
        if not self.scenario_instance._atomic_action_registered(name):
            return name
        else:
            name_template = name + " (%i)"
            atomic_action_iteration = 2
            while self.scenario_instance._atomic_action_registered(
                    name_template % atomic_action_iteration):
                atomic_action_iteration += 1
            return name_template % atomic_action_iteration

    def __exit__(self, type_, value, tb):
        super(AtomicAction, self).__exit__(type_, value, tb)
        if type_ is None:
            self.scenario_instance._add_atomic_actions(self.name,
                                                       self.duration())
