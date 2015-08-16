# Copyright 2014: Mirantis Inc.
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


import random
import time

from rally.task import atomic
from rally.task import scenario

# This is used to test relative import
from test_relative_import import zzz


class FakePlugin(scenario.Scenario):
    """Fake plugin with a scenario."""

    @atomic.action_timer("test1")
    def _test1(self, factor):
        time.sleep(random.random() * 0.1)

    @atomic.action_timer("test2")
    def _test2(self, factor):
        time.sleep(random.random() * factor)

    @scenario.configure()
    def testplugin(self, factor=1):
        """Fake scenario.

        :param factor: influences the argument value for a time.sleep() call
        """
        zzz.some_very_important_function()
        self._test1(factor)
        self._test2(factor)
