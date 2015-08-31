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

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.ceilometer import utils as cutils
from rally.plugins.openstack.scenarios.keystone import utils as kutils
from rally.task import validation


class CeilometerTraits(cutils.CeilometerScenario, kutils.KeystoneScenario):
    """Benchmark scenarios for Ceilometer Events API."""

    # NOTE(idegtiarov): to work with traits we need to create event firstly,
    # there are no other way except emit suitable notification from one of
    # services, for example create new user in keystone.

    @validation.required_services(consts.Service.CEILOMETER,
                                  consts.Service.KEYSTONE)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"],
                                 "cleanup": ["ceilometer"]})
    def create_user_and_list_traits(self):
        """Create user and fetch all event traits.

        This scenario creates user to store new event and
        fetches list of all traits for certain event type and
        trait name using GET /v2/event_types/<event_type>/traits/<trait_name>.
        """
        self._user_create()
        event = self._list_events()[0]
        trait_name = event.traits[0]["name"]
        self._list_event_traits(event_type=event.event_type,
                                trait_name=trait_name)

    @validation.required_services(consts.Service.CEILOMETER,
                                  consts.Service.KEYSTONE)
    @validation.required_openstack(admin=True)
    @scenario.configure(context={"admin_cleanup": ["keystone"],
                                 "cleanup": ["ceilometer"]})
    def create_user_and_list_trait_descriptions(self):
        """Create user and fetch all trait descriptions.

        This scenario creates user to store new event and
        fetches list of all traits for certain event type using
        GET /v2/event_types/<event_type>/traits.
        """
        self._user_create()
        event = self._list_events()[0]
        self._list_event_trait_descriptions(event_type=event.event_type)
