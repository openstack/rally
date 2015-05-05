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
import functools
import itertools
import random
import time

from rally.benchmark import functional
from rally.common import costilius
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import exceptions


LOG = logging.getLogger(__name__)


def scenario(context=None):
    """Make from plain python method benchmark.

       It sets 2 attributes to function:
       is_scenario = True # that is used during discovering
       func.context = context # default context for benchmark

       :param context: Default benchmark context
    """
    def wrapper(func):
        func.is_scenario = True
        func.context = context or {}
        return func
    return wrapper


class Scenario(functional.FunctionalMixin):
    """This is base class for any benchmark scenario.

       You should create subclass of this class. And your test scenarios will
       be auto discoverable and you will be able to specify it in test config.
    """
    RESOURCE_NAME_PREFIX = ""
    RESOURCE_NAME_LENGTH = 10

    def __init__(self, context=None, admin_clients=None, clients=None):
        self.context = context
        self._admin_clients = admin_clients
        self._clients = clients
        self._idle_duration = 0
        self._atomic_actions = costilius.OrderedDict()

    # TODO(amaretskiy): consider about prefix part of benchmark uuid
    @classmethod
    def _generate_random_name(cls, prefix=None, length=None):
        prefix = cls.RESOURCE_NAME_PREFIX if prefix is None else prefix
        length = length or cls.RESOURCE_NAME_LENGTH
        return utils.generate_random_name(prefix, length)

    @staticmethod
    def get_by_name(name):
        """Returns Scenario class by name."""
        for scenario in utils.itersubclasses(Scenario):
            if name == scenario.__name__:
                return scenario
        raise exceptions.NoSuchScenario(name=name)

    @staticmethod
    def get_scenario_by_name(name):
        """Return benchmark scenario method by name.

        :param name: name of the benchmark scenario being searched for (either
                     a full name (e.g, 'NovaServers.boot_server') or just
                     a method name (e.g., 'boot_server')
        :returns: function object
        """
        if "." in name:
            scenario_group, scenario_name = name.split(".", 1)
            scenario_cls = Scenario.get_by_name(scenario_group)
            if Scenario.is_scenario(scenario_cls, scenario_name):
                return getattr(scenario_cls, scenario_name)
        else:
            for scenario_cls in utils.itersubclasses(Scenario):
                if Scenario.is_scenario(scenario_cls, name):
                    return getattr(scenario_cls, name)
        raise exceptions.NoSuchScenario(name=name)

    @classmethod
    def list_benchmark_scenarios(scenario_cls):
        """List all scenarios in the benchmark scenario class & its subclasses.

        Returns the method names in format <Class name>.<Method name>, which
        is used in the test config.

        :param scenario_cls: the base class for searching scenarios in
        :returns: List of strings
        """
        scenario_classes = (list(utils.itersubclasses(scenario_cls)) +
                            [scenario_cls])
        benchmark_scenarios = [
            ["%s.%s" % (scenario.__name__, func)
             for func in dir(scenario) if Scenario.is_scenario(scenario, func)]
            for scenario in scenario_classes
        ]
        benchmark_scenarios_flattened = list(itertools.chain.from_iterable(
                                                        benchmark_scenarios))
        return benchmark_scenarios_flattened

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
        validators = cls.meta(name, "validators", default=[])

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

    @staticmethod
    def meta(cls, attr_name, method_name=None, default=None):
        """Extract the named meta information out of the scenario name.

        :param cls: Scenario (sub)class or string of form 'class.method'
        :param attr_name: Name of method attribute holding meta information.
        :param method_name: Name of method queried for meta information.
        :param default: Value returned if no meta information is attached.

        :returns: Meta value bound to method attribute or default.
        """
        if isinstance(cls, str):
            cls_name, method_name = cls.split(".", 1)
            cls = Scenario.get_by_name(cls_name)
        method = getattr(cls, method_name)
        return copy.deepcopy(getattr(method, attr_name, default))

    @staticmethod
    def is_scenario(cls, method_name):
        """Check whether a given method in scenario class is a scenario.

        :param cls: scenario class
        :param method_name: method name
        :returns: True if the method is a benchmark scenario, False otherwise
        """
        try:
            getattr(cls, method_name)
        except Exception:
            return False
        return Scenario.meta(cls, "is_scenario", method_name, default=False)

    def clients(self, client_type, version=None):
        """Returns a python openstack client of the requested type.

        The client will be that for one of the temporary non-administrator
        users created before the benchmark launch.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Standard python OpenStack client instance
        """
        client = getattr(self._clients, client_type)

        return client(version) if version is not None else client()

    def admin_clients(self, client_type, version=None):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)
        :param version: client version ("1"/"2" etc.)

        :returns: Python openstack client object
        """
        client = getattr(self._admin_clients, client_type)

        return client(version) if version is not None else client()

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

    def __exit__(self, type, value, tb):
        super(AtomicAction, self).__exit__(type, value, tb)
        if type is None:
            self.scenario_instance._add_atomic_actions(self.name,
                                                       self.duration())
