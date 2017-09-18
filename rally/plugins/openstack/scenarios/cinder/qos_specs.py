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


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderQos.create_and_list_qos", platform="openstack")
class CreateAndListQos(cinder_utils.CinderBasic):
    def run(self, consumer, write_iops_sec, read_iops_sec):
        """Create a qos, then list all qos.

        :param consumer: Consumer behavior
        :param write_iops_sec: random write limitation
        :param read_iops_sec: random read limitation
        """
        specs = {
            "consumer": consumer,
            "write_iops_sec": write_iops_sec,
            "read_iops_sec": read_iops_sec
        }

        qos = self.admin_cinder.create_qos(specs)

        pool_list = self.admin_cinder.list_qos()
        msg = ("Qos not included into list of available qos\n"
               "created qos:{}\n"
               "Pool of qos:{}").format(qos, pool_list)
        self.assertIn(qos, pool_list, err_msg=msg)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderQos.create_and_get_qos", platform="openstack")
class CreateAndGetQos(cinder_utils.CinderBasic):
    def run(self, consumer, write_iops_sec, read_iops_sec):
        """Create a qos, then get details of the qos.

        :param consumer: Consumer behavior
        :param write_iops_sec: random write limitation
        :param read_iops_sec: random read limitation
        """
        specs = {
            "consumer": consumer,
            "write_iops_sec": write_iops_sec,
            "read_iops_sec": read_iops_sec
        }

        qos = self.admin_cinder.create_qos(specs)
        self.admin_cinder.get_qos(qos.id)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderQos.create_and_set_qos", platform="openstack")
class CreateAndSetQos(cinder_utils.CinderBasic):
    def run(self, consumer, write_iops_sec, read_iops_sec,
            set_consumer, set_write_iops_sec, set_read_iops_sec):
        """Create a qos, then Add/Update keys in qos specs.

        :param consumer: Consumer behavior
        :param write_iops_sec: random write limitation
        :param read_iops_sec: random read limitation
        :param set_consumer: update Consumer behavior
        :param set_write_iops_sec: update random write limitation
        :param set_read_iops_sec: update random read limitation
        """
        create_specs = {
            "consumer": consumer,
            "write_iops_sec": write_iops_sec,
            "read_iops_sec": read_iops_sec
        }
        set_specs = {
            "consumer": set_consumer,
            "write_iops_sec": set_write_iops_sec,
            "read_iops_sec": set_read_iops_sec
        }

        qos = self.admin_cinder.create_qos(create_specs)
        self.admin_cinder.set_qos(qos=qos, set_specs_args=set_specs)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@validation.add("required_contexts", contexts=("volume_types"))
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderQos.create_qos_associate_and_disassociate_type",
    platform="openstack")
class CreateQosAssociateAndDisassociateType(cinder_utils.CinderBasic):
    def run(self, consumer, write_iops_sec, read_iops_sec):
        """Create a qos, Associate and Disassociate the qos from volume type.

        :param consumer: Consumer behavior
        :param write_iops_sec: random write limitation
        :param read_iops_sec: random read limitation
        """
        specs = {
            "consumer": consumer,
            "write_iops_sec": write_iops_sec,
            "read_iops_sec": read_iops_sec
        }

        qos = self.admin_cinder.create_qos(specs)

        vt_idx = self.context["iteration"] % len(self.context["volume_types"])
        volume_type = self.context["volume_types"][vt_idx]

        self.admin_cinder.qos_associate_type(qos_specs=qos,
                                             volume_type=volume_type["id"])

        self.admin_cinder.qos_disassociate_type(qos_specs=qos,
                                                volume_type=volume_type["id"])
