# Copyright 2015: Red Hat, Inc.
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
import uuid

from testtools import matchers

from rally.task import scenario
from tests.unit import test


class FunctionalMixinTestCase(test.TestCase):

    def test_implements_assertions(self):
        self.assertThat(
            dir(scenario.Scenario()),
            matchers.ContainsAll([
                "assertEqual",
                "assertNotEqual",
                "assertTrue",
                "assertFalse",
                "assertIs",
                "assertIsNot",
                "assertIsNone",
                "assertIsNotNone",
                "assertNotIn",
                "assertIsInstance",
                "assertIsNotInstance",
            ]),
        )


class AssertIsNotInstanceTestCase(test.TestCase):
    """Tests for `AssertIsNotInstance`."""

    def test_raises_when_type_matches(self):
        self.assertRaises(
            matchers._impl.MismatchError,
            scenario.Scenario().assertIsNotInstance,
            random.randint(1, 100),
            int,
        )

    def test_returns_none_when_instance_does_not_matche_type(self):
        random_str = uuid.uuid4()
        self.assertIsNone(
            scenario.Scenario().assertIsNotInstance(random_str, int))
