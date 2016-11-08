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
from rally.plugins.openstack.scenarios.ceilometer import utils as ceiloutils
from rally.task import validation

"""Benchmark scenarios for Ceilometer Alarms API."""


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_alarm")
class CreateAlarm(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, **kwargs):
        """Create an alarm.

        This scenarios test POST /v2/alarms.
        meter_name and threshold are required parameters for alarm creation.
        kwargs stores other optional parameters like 'ok_actions',
        'project_id' etc that may be passed while creating an alarm.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """

        self._create_alarm(meter_name, threshold, kwargs)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(name="CeilometerAlarms.list_alarms")
class ListAlarms(ceiloutils.CeilometerScenario):

    def run(self):
        """Fetch all alarms.

        This scenario fetches list of all alarms using GET /v2/alarms.
        """
        self._list_alarms()


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_and_list_alarm")
class CreateAndListAlarm(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, **kwargs):
        """Create and get the newly created alarm.

        This scenarios test GET /v2/alarms/(alarm_id)
        Initially alarm is created and then the created alarm is fetched using
        its alarm_id. meter_name and threshold are required parameters
        for alarm creation. kwargs stores other optional parameters like
        'ok_actions', 'project_id' etc. that may be passed while creating
        an alarm.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        self._list_alarms(alarm.alarm_id)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_and_get_alarm")
class CreateAndGetAlarm(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, **kwargs):
        """Create and get the newly created alarm.

        These scenarios test GET /v2/alarms/(alarm_id)
        Initially an alarm is created and then its detailed information is
        fetched using its alarm_id. meter_name and threshold are required
        parameters for alarm creation. kwargs stores other optional parameters
        like 'ok_actions', 'project_id' etc. that may be passed while creating
        an alarm.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        self._get_alarm(alarm.alarm_id)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_and_update_alarm")
class CreateAndUpdateAlarm(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, **kwargs):
        """Create and update the newly created alarm.

        This scenarios test PUT /v2/alarms/(alarm_id)
        Initially alarm is created and then the created alarm is updated using
        its alarm_id. meter_name and threshold are required parameters
        for alarm creation. kwargs stores other optional parameters like
        'ok_actions', 'project_id' etc that may be passed while alarm creation.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        alarm_dict_diff = {"description": "Changed Test Description"}
        self._update_alarm(alarm.alarm_id, alarm_dict_diff)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_and_delete_alarm")
class CreateAndDeleteAlarm(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, **kwargs):
        """Create and delete the newly created alarm.

        This scenarios test DELETE /v2/alarms/(alarm_id)
        Initially alarm is created and then the created alarm is deleted using
        its alarm_id. meter_name and threshold are required parameters
        for alarm creation. kwargs stores other optional parameters like
        'ok_actions', 'project_id' etc that may be passed while alarm creation.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        self._delete_alarm(alarm.alarm_id)


@validation.required_services(consts.Service.CEILOMETER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["ceilometer"]},
                    name="CeilometerAlarms.create_alarm_and_get_history")
class CreateAlarmAndGetHistory(ceiloutils.CeilometerScenario):

    def run(self, meter_name, threshold, state, timeout=60, **kwargs):
        """Create an alarm, get and set the state and get the alarm history.

         This scenario makes following queries:
            GET /v2/alarms/{alarm_id}/history
            GET /v2/alarms/{alarm_id}/state
            PUT /v2/alarms/{alarm_id}/state
        Initially alarm is created and then get the state of the created alarm
        using its alarm_id. Then get the history of the alarm. And finally the
        state of the alarm is updated using given state. meter_name and
        threshold are required parameters for alarm creation. kwargs stores
        other optional parameters like 'ok_actions', 'project_id' etc that may
        be passed while alarm creation.

        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param state: an alarm state to be set
        :param timeout: The number of seconds for which to attempt a
                        successful check of the alarm state
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        self._get_alarm_state(alarm.alarm_id)
        self._get_alarm_history(alarm.alarm_id)
        self._set_alarm_state(alarm, state, timeout)
