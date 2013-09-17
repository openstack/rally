# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import unittest2

from rally.benchmark import utils


class FakeTest(unittest2.TestCase):

    # NOTE(msdubov): The class is introduced for testing purposes exclusively;
    #                it's been placed here because the TestEngine looks up the
    #                tests under the 'rally' directory.

    @utils.parameterize_from_test_config('fake')
    def test_parameterize(self, arg=1):
        # NOTE(msdubov): The method is called just from one single test case
        #                with config specifying the arg value changed to 5.
        self.assertEqual(arg, 5)
