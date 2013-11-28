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

from rally import exceptions
from rally import utils


class Scenario(object):
    """This is base class for any benchmark scenario.
       You should create subclass of this class. And you test scnerios will
       be autodiscoverd and you will be able to specify it in test config.
    """
    registred = False

    @staticmethod
    def register():
        if not Scenario.registred:
            utils.import_modules_from_package("rally.benchmark.scenarios")
            Scenario.registred = True

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
        utils.import_modules_from_package("rally.benchmark.scenarios")
        benchmark_scenarios = [
            ["%s.%s" % (scenario.__name__, method)
             for method in dir(scenario) if not method.startswith("_")]
            for scenario in utils.itersubclasses(Scenario)
        ]
        benchmark_scenarios_flattened = list(itertools.chain.from_iterable(
                                                        benchmark_scenarios))
        return benchmark_scenarios_flattened

    @classmethod
    def init(cls, config):
        """This method will be called with test config. It purpose is to
            prepare test enviorment. E.g. if you would like to test
            performance of assing of FloatingIps here you will create 200k
            FloatinigIps anre retun information about it to
        """
        return {}

    @classmethod
    def cleanup(cls):
        """This method should free all allocated resources."""

    @classmethod
    def context(cls):
        """Returns the context of the current benchmark scenario.

        The context is the return value of the init() class.

        :returns: Dict
        """
        return cls._context

    @classmethod
    def clients(cls, client_type):
        """Returns a python openstack client of the requested type.

        The client will be that for one of the temporary non-administrator
        users created before the benchmark launch.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Python openstack client object
        """
        return cls._clients[client_type]

    @classmethod
    def admin_clients(cls, client_type):
        """Returns a python admin openstack client of the requested type.

        :param client_type: Client type ("nova"/"glance" etc.)

        :returns: Python openstack client object
        """
        return cls._admin_clients[client_type]

    @classmethod
    def sleep_between(cls, min_sleep, max_sleep):
        """Performs a time.sleep() call for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_time class
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        """
        if not 0 <= min_sleep <= max_sleep:
            raise exceptions.InvalidArgumentsException(
                                        message="0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        time.sleep(sleep_time)
        cls.idle_time += sleep_time
