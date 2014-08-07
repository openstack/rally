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

from rally.benchmark.scenarios import base as scenario_base
from rally.benchmark.scenarios.ceilometer import utils as ceilometerutils
from rally.benchmark import validation
from rally import consts


class CeilometerAlarms(ceilometerutils.CeilometerScenario):
    @scenario_base.scenario(context={"cleanup": ["ceilometer"]})
    @validation.required_services(consts.Service.CEILOMETER)
    def create_alarm(self, meter_name, threshold, **kwargs):
        """Test creating an alarm.

        This scenarios test POST /v2/alarms.
        meter_name and threshold are required parameters for alarm creation.
        kwargs stores other optional parameters like 'ok_actions',
        'project_id' etc that may be passed while creating alarm.
        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        self._create_alarm(meter_name, threshold, kwargs)

    @scenario_base.scenario()
    @validation.required_services(consts.Service.CEILOMETER)
    def list_alarms(self):
        """Test fetching all alarms.

        This scenario fetches list of all alarms using GET /v2/alarms.
        """
        self._list_alarms()

    @scenario_base.scenario(context={"cleanup": ["ceilometer"]})
    @validation.required_services(consts.Service.CEILOMETER)
    def create_and_list_alarm(self, meter_name, threshold, **kwargs):
        """Test creating and getting newly created alarm.

        This scenarios test GET /v2/alarms/(alarm_id)
        Initially alarm is created and then the created alarm is fetched using
        its alarm_id. meter_name and threshold are required parameters
        for alarm creation. kwargs stores other optional parameters like
        'ok_actions', 'project_id' etc. that may be passed while creating alarm
        :param meter_name: specifies meter name of the alarm
        :param threshold: specifies alarm threshold
        :param kwargs: specifies optional arguments for alarm creation.
        """
        alarm = self._create_alarm(meter_name, threshold, kwargs)
        self._list_alarms(alarm.alarm_id)

    @scenario_base.scenario(context={"cleanup": ["ceilometer"]})
    @validation.required_services(consts.Service.CEILOMETER)
    def create_and_update_alarm(self, meter_name, threshold, **kwargs):
        """Test creating and updating the newly created alarm.

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

    @scenario_base.scenario(context={"cleanup": ["ceilometer"]})
    @validation.required_services(consts.Service.CEILOMETER)
    def create_and_delete_alarm(self, meter_name, threshold, **kwargs):
        """Test creating and deleting the newly created alarm.

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
