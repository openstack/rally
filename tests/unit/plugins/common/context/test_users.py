# Copyright 2017: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.common.context import users
from tests.unit import test


class NoUserTestCase(test.TestCase):

    def test_setup(self):
        context = {"task": mock.MagicMock(), "config": {}}
        users.NoUsers(context).setup()
        self.assertIn("users", context)
        self.assertEqual([], context["users"])

    def test_cleanup(self):
        # NOTE(astudenov): Test that cleanup is not abstract
        users.NoUsers({"task": mock.MagicMock()}).cleanup()
