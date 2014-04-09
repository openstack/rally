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

import itertools
import random
import time

from rally import consts
from rally import exceptions
from rally import utils


def scenario(admin_only=False, context=None):
    """This method is used as decorator for the methods of benchmark scenarios
       and it adds following extra fields to the methods.
       'is_scenario' is set to True
       'admin_only' is set to True if a scenario require admin endpoints
    """
    def wrapper(func):
        func.is_scenario = True
        func.admin_only = admin_only
        func.context = context or {}
        return func
    return wrapper


class Scenario(object):
    """This is base class for any benchmark scenario.
       You should create subclass of this class. And you test scenarios will
       be auto discoverable and you will be able to specify it in test config.
    """
    def __init__(self, context=None, admin_clients=None, clients=None):
        self._context = context
        self._admin_clients = admin_clients
        self._clients = clients
        self._idle_duration = 0
        self._atomic_actions = []

    @staticmethod
    def get_by_name(name):
        """Returns Scenario class by name."""
        for scenario in utils.itersubclasses(Scenario):
            if name == scenario.__name__:
                return scenario
        raise exceptions.NoSuchScenario(name=name)

    @staticmethod
    def list_benchmark_scenarios():
        """Lists all the existing methods in the benchmark scenario classes.

        Returns the method names in format <Class name>.<Method name>, which
        is used in the test config.

        :returns: List of strings
        """
        benchmark_scenarios = [
            ["%s.%s" % (scenario.__name__, method)
             for method in dir(scenario)
                if Scenario.meta(scenario, method_name=method,
                                 attr_name="is_scenario", default=False)]
            for scenario in utils.itersubclasses(Scenario)
        ]
        benchmark_scenarios_flattened = list(itertools.chain.from_iterable(
                                                        benchmark_scenarios))
        return benchmark_scenarios_flattened

    @staticmethod
    def _validate_helper(validators, clients, args):
        for validator in validators:
            result = validator(clients=clients, **args)
            if not result.is_valid:
                raise exceptions.InvalidScenarioArgument(message=result.msg)

    @staticmethod
    def validate(name, args, admin=None, users=None):
        """Semantic check of benchmark arguments."""
        validators = Scenario.meta(name, "validators", default=[])

        if not validators:
            return

        admin_validators = [v for v in validators
                            if v.permission == consts.EndpointPermission.ADMIN]
        user_validators = [v for v in validators
                           if v.permission == consts.EndpointPermission.USER]

        # NOTE(boris-42): Potential bug, what if we don't have "admin" client
        #                 and scenario have "admin" validators.
        if admin:
            Scenario._validate_helper(admin_validators, admin, args)
        if users:
            for user in users:
                Scenario._validate_helper(user_validators, user, args)

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
        return getattr(method, attr_name, default)

    def context(self):
        """Returns the context of the current benchmark scenario."""
        return self._context

    def clients(self, client_type):
        """Returns a python openstack client of the requested type.

        The client will be that for one of the temporary non-administrator
        users created before the benchmark launch.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Standard python OpenStack client instance
        """
        return getattr(self._clients, client_type)()

    def admin_clients(self, client_type):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Python openstack client object
        """
        return getattr(self._admin_clients, client_type)()

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
                                        message="0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)
        self._idle_duration += sleep_time

    def idle_duration(self):
        """Returns duration of all sleep_between."""
        return self._idle_duration

    def _add_atomic_actions(self, name, duration):
        """Adds the duration of an atomic action by its 'name'."""
        self._atomic_actions.append(
            {'action': name, 'duration': duration})

    def atomic_actions(self):
        """Returns the content of each atomic action."""
        return self._atomic_actions
