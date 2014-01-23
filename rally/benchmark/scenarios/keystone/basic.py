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

from rally.benchmark.scenarios.keystone import utils as kutils


class KeystoneBasic(kutils.KeystoneScenario):

    def create_user(self, name_length=10, **kwargs):
        self._user_create(name_length=name_length, **kwargs)

    def create_delete_user(self, name_length=10, **kwargs):
        user = self._user_create(name_length=name_length, **kwargs)
        self._resource_delete(user)
