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
from rally.plugins.openstack.scenarios.keystone import basic as kbasic
from rally.task import validation


"""Scenarios for Ceilometer Events API."""


# NOTE(idegtiarov): to work with traits we need to create event firstly,
# there are no other way except emit suitable notification from one of
# services, for example create new user in keystone.

@validation.add("required_services", services=[consts.Service.CEILOMETER,
                                               consts.Service.KEYSTONE])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["keystone"],
             "cleanup@openstack": ["ceilometer"]},
    name="CeilometerTraits.create_user_and_list_traits",
    platform="openstack")
class CreateUserAndListTraits(cutils.CeilometerScenario,
                              kbasic.KeystoneBasic):

    def run(self):
        """Create user and fetch all event traits.

        This scenario creates user to store new event and
        fetches list of all traits for certain event type and
        trait name using GET /v2/event_types/<event_type>/traits/<trait_name>.
        """
        self.admin_keystone.create_user()
        event = self._list_events()[0]
        trait_name = event.traits[0]["name"]
        self._list_event_traits(event_type=event.event_type,
                                trait_name=trait_name)


@validation.add("required_services", services=[consts.Service.CEILOMETER,
                                               consts.Service.KEYSTONE])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["keystone"],
             "cleanup@openstack": ["ceilometer"]},
    name="CeilometerTraits.create_user_and_list_trait_descriptions",
    platform="openstack")
class CreateUserAndListTraitDescriptions(
        cutils.CeilometerScenario, kbasic.KeystoneBasic):

    def run(self):
        """Create user and fetch all trait descriptions.

        This scenario creates user to store new event and
        fetches list of all traits for certain event type using
        GET /v2/event_types/<event_type>/traits.
        """
        self.admin_keystone.create_user()
        event = self._list_events()[0]
        self._list_event_trait_descriptions(event_type=event.event_type)
