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

# NOTE(msdubov): This file contains the pre-defined mappings from test names
#                to pytest arguments passed while launching these tests. The
#                test names listed here should be used in test configuration
#                files.

verification_tests = {
    'sanity': ['--pyargs', 'fuel_health.tests.sanity'],
    'smoke': ['--pyargs', 'fuel_health.tests.smoke', '-k',
              '"not (test_007 or test_008 or test_009 or test_snapshot)"'],
    'snapshot': ['--pyargs', 'fuel_health.tests.smoke', '-k',
                 '"test_snapshot"']
}

# TODO(msdubov): Implement an automatic benchmark tests collector.
benchmark_tests = {}

tests = {'verify': verification_tests, 'benchmark': benchmark_tests}
