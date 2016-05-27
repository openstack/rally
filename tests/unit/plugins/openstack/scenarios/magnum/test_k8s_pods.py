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

import ddt
import mock

from rally import exceptions
from rally.plugins.openstack.scenarios.magnum import k8s_pods
from tests.unit import test


@ddt.ddt
class K8sPodsTestCase(test.ScenarioTestCase):

    def test_list_pods(self):
        scenario = k8s_pods.ListPods()
        scenario._list_v1pods = mock.Mock()

        scenario.run()

        scenario._list_v1pods.assert_called_once_with()

    @ddt.data(["manifest.json"], ["manifest.yaml"])
    def test_create_pods(self, manifests):
        manifest = manifests[0]
        scenario = k8s_pods.CreatePods()
        file_content = "data: fake_content"
        if manifest == "manifest.json":
            file_content = "{\"data\": \"fake_content\"}"
        file_mock = mock.mock_open(read_data=file_content)
        fake_pod = mock.Mock()
        scenario._create_v1pod = mock.MagicMock(return_value=fake_pod)

        with mock.patch(
                "rally.plugins.openstack.scenarios.magnum.k8s_pods.open",
                file_mock, create=True) as m:
            scenario.run(manifests)

        m.assert_called_once_with(manifest, "r")
        m.return_value.read.assert_called_once_with()
        scenario._create_v1pod.assert_called_once_with(
            {"data": "fake_content"})

        # test error cases:
        # 1. pod not created
        scenario._create_v1pod = mock.MagicMock(return_value=None)

        with mock.patch(
                "rally.plugins.openstack.scenarios.magnum.k8s_pods.open",
                file_mock, create=True) as m:
            self.assertRaises(
                exceptions.RallyAssertionError,
                scenario.run, manifests)

        m.assert_called_with(manifest, "r")
        m.return_value.read.assert_called_with()
        scenario._create_v1pod.assert_called_with(
            {"data": "fake_content"})

    @ddt.data(["manifest.json"], ["manifest.yaml"])
    def test_create_rcs(self, manifests):
        manifest = manifests[0]
        scenario = k8s_pods.CreateRcs()
        file_content = "data: fake_content"
        if manifest == "manifest.json":
            file_content = "{\"data\": \"fake_content\"}"
        file_mock = mock.mock_open(read_data=file_content)
        fake_rc = mock.Mock()
        scenario._create_v1rc = mock.MagicMock(return_value=fake_rc)

        with mock.patch(
                "rally.plugins.openstack.scenarios.magnum.k8s_pods.open",
                file_mock, create=True) as m:
            scenario.run(manifests)

        m.assert_called_once_with(manifest, "r")
        m.return_value.read.assert_called_once_with()
        scenario._create_v1rc.assert_called_once_with({"data": "fake_content"})

        # test error cases:
        # 1. rc not created
        scenario._create_v1rc = mock.MagicMock(return_value=None)

        with mock.patch(
                "rally.plugins.openstack.scenarios.magnum.k8s_pods.open",
                file_mock, create=True) as m:
            self.assertRaises(
                exceptions.RallyAssertionError,
                scenario.run, manifests)

        m.assert_called_with(manifest, "r")
        m.return_value.read.assert_called_with()
        scenario._create_v1rc.assert_called_with({"data": "fake_content"})
