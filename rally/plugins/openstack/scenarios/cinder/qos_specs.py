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
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.task import validation


"""Scenarios for Cinder QoS."""


@validation.restricted_parameters("name")
@validation.required_services(consts.Service.CINDER)
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderQos.create_and_list_qos")
class CreateAndListQos(cinder_utils.CinderBasic):
    def run(self, specs):
        """create a qos, then list all qos.

        :param specs: A dict of key/value pairs to create qos
        """
        qos = self.admin_cinder.create_qos(specs)

        pool_list = self.admin_cinder.list_qos()
        msg = ("Qos not included into list of available qos\n"
               "created qos:{}\n"
               "Pool of qos:{}").format(qos, pool_list)
        self.assertIn(qos, pool_list, err_msg=msg)


@validation.restricted_parameters("name")
@validation.required_services(consts.Service.CINDER)
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup": ["cinder"]},
                    name="CinderQos.create_and_get_qos")
class CreateAndGetQos(cinder_utils.CinderBasic):
    def run(self, specs):
        """Create a qos, then get details of the qos.

        :param specs: A dict of key/value pairs to create qos
        """
        qos = self.admin_cinder.create_qos(specs)
        self.admin_cinder.get_qos(qos.id)
