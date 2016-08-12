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


# NOTE(idegtiarov): to work with event we need to create it, there are
# no other way except emit suitable notification from one of services,
# for example create new user in keystone.

@validation.required_services(consts.Service.CEILOMETER,
                              consts.Service.KEYSTONE)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"],
                             "cleanup": ["ceilometer"]},
                    name="CeilometerEvents.create_user_and_list_events")
class CeilometerEventsCreateUserAndListEvents(cutils.CeilometerScenario,
                                              kutils.KeystoneScenario):
    """Benchmark scenarios for Ceilometer Events API."""
    def run(self):
        """Create user and fetch all events.

        This scenario creates user to store new event and
        fetches list of all events using GET /v2/events.
        """
        self._user_create()
        self._list_events()


@validation.required_services(consts.Service.CEILOMETER,
                              consts.Service.KEYSTONE)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"],
                             "cleanup": ["ceilometer"]},
                    name="CeilometerEvents.create_user_and_list_event_types")
class CeilometerEventsCreateUserAndListEventTypes(cutils.CeilometerScenario,
                                                  kutils.KeystoneScenario):
    """Benchmark scenarios for Ceilometer Events API."""
    def run(self):
        """Create user and fetch all event types.

        This scenario creates user to store new event and
        fetches list of all events types using GET /v2/event_types.
        """
        self._user_create()
        self._list_event_types()


@validation.required_services(consts.Service.CEILOMETER,
                              consts.Service.KEYSTONE)
@validation.required_openstack(admin=True)
@scenario.configure(context={"admin_cleanup": ["keystone"],
                             "cleanup": ["ceilometer"]},
                    name="CeilometerEvents.create_user_and_get_event")
class CeilometerEventsCreateUserAndGetEvent(cutils.CeilometerScenario,
                                            kutils.KeystoneScenario):
    """Benchmark scenarios for Ceilometer Events API."""
    def run(self):
        """Create user and gets event.

        This scenario creates user to store new event and
        fetches one event using GET /v2/events/<message_id>.
        """
        self._user_create()
        event = self._list_events()[0]
        self._get_event(event_id=event.message_id)
