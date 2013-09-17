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

import os

import fuel_health.manager
import fuel_health.test

from rally.benchmark import config


class ParameterizableTestCase(fuel_health.test.TestCase):

    manager_class = fuel_health.manager.Manager

    def setUp(self):
        super(ParameterizableTestCase, self).setUp()
        # NOTE(msdubov): setUp method parametrization from test configuration;
        #                the passed parameters can then be used in subclasses
        #                via the self._get_param() method.
        test_config = config.TestConfigManager(os.environ['PYTEST_CONFIG'])
        tests_setUp = test_config.to_dict()['benchmark'].get('tests_setUp', {})
        self._params = tests_setUp.get(self.benchmark_name, {})

    def _get_param(self, param_name, default_value=None):
        return self._params.get(param_name, default_value)
