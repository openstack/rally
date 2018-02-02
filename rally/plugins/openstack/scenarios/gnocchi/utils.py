# Copyright 2017 Red Hat, Inc. <http://www.redhat.com>
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

from rally.plugins.openstack import scenario
from rally.plugins.openstack.services.gnocchi import metric


class GnocchiBase(scenario.OpenStackScenario):
    """Base class for Gnocchi scenarios with basic atomic actions."""

    def __init__(self, context=None, admin_clients=None, clients=None):
        super(GnocchiBase, self).__init__(context, admin_clients, clients)
        if hasattr(self, "_admin_clients"):
            self.admin_gnocchi = metric.GnocchiService(
                self._admin_clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())
        if hasattr(self, "_clients"):
            self.gnocchi = metric.GnocchiService(
                self._clients, name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())
