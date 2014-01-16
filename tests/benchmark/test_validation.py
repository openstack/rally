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

from rally.benchmark import validation
from tests import test


class ValidationUtilsTestCase(test.TestCase):

    def test_add_validator(self):
        def test_validator():
            pass

        @validation.add_validator(test_validator)
        def test_function():
            pass

        validators = getattr(test_function, "validators")
        self.assertEqual(len(validators), 1)
        self.assertEqual(validators[0], test_validator)
