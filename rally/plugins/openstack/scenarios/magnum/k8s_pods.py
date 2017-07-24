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

import yaml

from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.magnum import utils
from rally.task import validation


"""Scenarios for Kubernetes pods and rcs."""


@validation.add("required_services", services=consts.Service.MAGNUM)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="K8sPods.list_pods", platform="openstack")
class ListPods(utils.MagnumScenario):

    def run(self):
        """List all pods.

        """
        self._list_v1pods()


@validation.add("required_services", services=consts.Service.MAGNUM)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="K8sPods.create_pods", platform="openstack")
class CreatePods(utils.MagnumScenario):

    def run(self, manifests):
        """create pods and wait for them to be ready.

        :param manifests: manifest files used to create the pods
        """
        for manifest in manifests:
            with open(manifest, "r") as f:
                manifest_str = f.read()
            manifest = yaml.load(manifest_str)
            pod = self._create_v1pod(manifest)
            msg = ("Pod isn't created")
            self.assertTrue(pod, err_msg=msg)


@validation.add("required_services", services=consts.Service.MAGNUM)
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="K8sPods.create_rcs", platform="openstack")
class CreateRcs(utils.MagnumScenario):

    def run(self, manifests):
        """create rcs and wait for them to be ready.

        :param manifests: manifest files use to create the rcs
        """
        for manifest in manifests:
            with open(manifest, "r") as f:
                manifest_str = f.read()
            manifest = yaml.load(manifest_str)
            rc = self._create_v1rc(manifest)
            msg = ("RC isn't created")
            self.assertTrue(rc, err_msg=msg)
