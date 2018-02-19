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

import os

import mock

from kubernetes import client as kubernetes_client
from kubernetes.client import api_client
from kubernetes.client.rest import ApiException
from rally import exceptions
from rally.plugins.openstack.scenarios.magnum import utils
from tests.unit import test

MAGNUM_UTILS = "rally.plugins.openstack.scenarios.magnum.utils"

CONF = utils.CONF


class MagnumScenarioTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(MagnumScenarioTestCase, self).setUp()
        self.cluster_template = mock.Mock()
        self.cluster = mock.Mock()
        self.pod = mock.Mock()
        self.scenario = utils.MagnumScenario(self.context)

    def test_list_cluster_templates(self):
        fake_list = [self.cluster_template]

        self.clients("magnum").cluster_templates.list.return_value = fake_list
        return_ct_list = self.scenario._list_cluster_templates()
        self.assertEqual(fake_list, return_ct_list)

        self.clients("magnum").cluster_templates.list.assert_called_once_with()
        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "magnum.list_cluster_templates")

    def test_create_cluster_template(self):
        self.scenario.generate_random_name = mock.Mock(
            return_value="generated_name")
        fake_ct = self.cluster_template
        self.clients("magnum").cluster_templates.create.return_value = fake_ct

        return_cluster_template = self.scenario._create_cluster_template(
            image="test_image",
            keypair="test_key",
            external_network="public",
            dns_nameserver="8.8.8.8",
            flavor="m1.large",
            docker_volume_size=50,
            network_driver="docker",
            coe="swarm")

        self.assertEqual(fake_ct, return_cluster_template)
        _, kwargs = self.clients("magnum").cluster_templates.create.call_args
        self.assertEqual("generated_name", kwargs["name"])

        self._test_atomic_action_timer(self.scenario.atomic_actions(),
                                       "magnum.create_cluster_template")

    def test_get_cluster_template(self):
        client = self.clients("magnum")
        client.cluster_templates.get.return_value = self.cluster_template
        return_cluster_template = self.scenario._get_cluster_template("uuid")
        client.cluster_templates.get.assert_called_once_with("uuid")
        self.assertEqual(self.cluster_template, return_cluster_template)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.get_cluster_template")

    def test_list_clusters(self):
        return_clusters_list = self.scenario._list_clusters(limit="foo1")
        client = self.clients("magnum")
        client.clusters.list.assert_called_once_with(limit="foo1")
        self.assertEqual(client.clusters.list.return_value,
                         return_clusters_list)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.list_clusters")

    def test_create_cluster(self):
        self.scenario.generate_random_name = mock.Mock(
            return_value="generated_name")
        self.clients("magnum").clusters.create.return_value = self.cluster
        return_cluster = self.scenario._create_cluster(
            cluster_template="generated_uuid", node_count=2)
        self.mock_wait_for_status.mock.assert_called_once_with(
            self.cluster,
            ready_statuses=["CREATE_COMPLETE"],
            update_resource=self.mock_get_from_manager.mock.return_value,
            check_interval=CONF.openstack.
            magnum_cluster_create_poll_interval,
            timeout=CONF.openstack.magnum_cluster_create_timeout,
            id_attr="uuid")
        _, kwargs = self.clients("magnum").clusters.create.call_args
        self.assertEqual("generated_name", kwargs["name"])
        self.assertEqual("generated_uuid", kwargs["cluster_template_id"])
        self.mock_get_from_manager.mock.assert_called_once_with()
        self.assertEqual(
            self.mock_wait_for_status.mock.return_value, return_cluster)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.create_cluster")

    def test_get_cluster(self):
        self.clients("magnum").clusters.get.return_value = self.cluster
        return_cluster = self.scenario._get_cluster("uuid")
        self.clients("magnum").clusters.get.assert_called_once_with("uuid")
        self.assertEqual(self.cluster, return_cluster)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.get_cluster")

    def test_get_ca_certificate(self):
        self.scenario._get_ca_certificate(self.cluster.uuid)
        self.clients("magnum").certificates.get.assert_called_once_with(
            self.cluster.uuid)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.get_ca_certificate")

    def test_create_ca_certificate(self):
        csr_req = {"cluster_uuid": "uuid", "csr": "csr file"}
        self.scenario._create_ca_certificate(csr_req)
        self.clients("magnum").certificates.create.assert_called_once_with(
            **csr_req)
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.create_ca_certificate")

    @mock.patch("kubernetes.client.api_client.ApiClient")
    @mock.patch("kubernetes.client.apis.core_v1_api.CoreV1Api")
    def test_get_k8s_api_client_using_tls(self, mock_core_v1_api,
                                          mock_api_client):

        if hasattr(kubernetes_client, "ConfigurationObject"):
            # it is k8s-client < 4.0.0
            m = mock.patch("kubernetes.client.ConfigurationObject")
        else:
            m = mock.patch("kubernetes.client.Configuration")

        mock_configuration_object = m.start()
        self.addCleanup(m.stop)

        self.context.update({
            "ca_certs_directory": "/home/stack",
            "tenant": {
                "id": "rally_tenant_id",
                "cluster": "rally_cluster_uuid"
            }
        })
        self.scenario = utils.MagnumScenario(self.context)
        cluster_uuid = self.context["tenant"]["cluster"]
        client = self.clients("magnum")
        client.clusters.get.return_value = self.cluster
        cluster = self.scenario._get_cluster(cluster_uuid)
        self.cluster_template.tls_disabled = False
        client.cluster_templates.get.return_value = self.cluster_template
        dir = self.context["ca_certs_directory"]
        key_file = os.path.join(dir, cluster_uuid.__add__(".key"))
        cert_file = os.path.join(dir, cluster_uuid.__add__(".crt"))
        ca_certs = os.path.join(dir, cluster_uuid.__add__("_ca.crt"))
        config = mock_configuration_object.return_value
        config.host = cluster.api_address
        config.ssl_ca_cert = ca_certs
        config.cert_file = cert_file
        config.key_file = key_file
        _api_client = mock_api_client.return_value
        self.scenario._get_k8s_api_client()
        mock_configuration_object.assert_called_once_with()
        mock_api_client.assert_called_once_with(config=config)
        mock_core_v1_api.assert_called_once_with(_api_client)

    @mock.patch("kubernetes.client.api_client.ApiClient")
    @mock.patch("kubernetes.client.apis.core_v1_api.CoreV1Api")
    def test_get_k8s_api_client(self, mock_core_v1_api, mock_api_client):

        if hasattr(kubernetes_client, "ConfigurationObject"):
            # it is k8s-client < 4.0.0
            m = mock.patch("kubernetes.client.ConfigurationObject")
        else:
            m = mock.patch("kubernetes.client.Configuration")

        mock_configuration_object = m.start()
        self.addCleanup(m.stop)

        self.context.update({
            "tenant": {
                "id": "rally_tenant_id",
                "cluster": "rally_cluster_uuid"
            }
        })
        self.scenario = utils.MagnumScenario(self.context)
        cluster_uuid = self.context["tenant"]["cluster"]
        client = self.clients("magnum")
        client.clusters.get.return_value = self.cluster
        cluster = self.scenario._get_cluster(cluster_uuid)
        self.cluster_template.tls_disabled = True
        client.cluster_templates.get.return_value = self.cluster_template
        config = mock_configuration_object.return_value
        config.host = cluster.api_address
        config.ssl_ca_cert = None
        config.cert_file = None
        config.key_file = None
        _api_client = mock_api_client.return_value
        self.scenario._get_k8s_api_client()
        mock_configuration_object.assert_called_once_with()
        mock_api_client.assert_called_once_with(config=config)
        mock_core_v1_api.assert_called_once_with(_api_client)

    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_list_v1pods(self, mock__get_k8s_api_client):
        k8s_api = mock__get_k8s_api_client.return_value
        self.scenario._list_v1pods()
        k8s_api.list_node.assert_called_once_with(
            namespace="default")
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.k8s_list_v1pods")

    @mock.patch("random.choice")
    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_create_v1pod(self, mock__get_k8s_api_client,
                          mock_random_choice):
        k8s_api = mock__get_k8s_api_client.return_value
        manifest = (
            {"apiVersion": "v1", "kind": "Pod",
             "metadata": {"name": "nginx"}})
        podname = manifest["metadata"]["name"] + "-"
        for i in range(5):
            podname = podname + mock_random_choice.return_value
        k8s_api.create_namespaced_pod = mock.MagicMock(
            side_effect=[ApiException(status=403), self.pod])
        not_ready_pod = api_client.models.V1Pod()
        not_ready_status = api_client.models.V1PodStatus()
        not_ready_status.phase = "not_ready"
        not_ready_pod.status = not_ready_status
        almost_ready_pod = api_client.models.V1Pod()
        almost_ready_status = api_client.models.V1PodStatus()
        almost_ready_status.phase = "almost_ready"
        almost_ready_pod.status = almost_ready_status
        ready_pod = api_client.models.V1Pod()
        ready_condition = api_client.models.V1PodCondition(status="True",
                                                           type="Ready")
        ready_status = api_client.models.V1PodStatus()
        ready_status.phase = "Running"
        ready_status.conditions = [ready_condition]
        ready_pod_metadata = api_client.models.V1ObjectMeta()
        ready_pod_metadata.uid = "123456789"
        ready_pod_spec = api_client.models.V1PodSpec(
            node_name="host_abc",
            containers=[]
        )
        ready_pod.status = ready_status
        ready_pod.metadata = ready_pod_metadata
        ready_pod.spec = ready_pod_spec
        k8s_api.read_namespaced_pod = mock.MagicMock(
            side_effect=[not_ready_pod, almost_ready_pod, ready_pod])
        self.scenario._create_v1pod(manifest)
        k8s_api.create_namespaced_pod.assert_called_with(
            body=manifest, namespace="default")
        k8s_api.read_namespaced_pod.assert_called_with(
            name=podname, namespace="default")
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.k8s_create_v1pod")

    @mock.patch("time.time")
    @mock.patch("random.choice")
    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_create_v1pod_timeout(self, mock__get_k8s_api_client,
                                  mock_random_choice, mock_time):
        k8s_api = mock__get_k8s_api_client.return_value
        manifest = (
            {"apiVersion": "v1", "kind": "Pod",
             "metadata": {"name": "nginx"}})
        k8s_api.create_namespaced_pod.return_value = self.pod
        mock_time.side_effect = [1, 2, 3, 4, 5, 1800, 1801]
        not_ready_pod = api_client.models.V1Pod()
        not_ready_status = api_client.models.V1PodStatus()
        not_ready_status.phase = "not_ready"
        not_ready_pod_metadata = api_client.models.V1ObjectMeta()
        not_ready_pod_metadata.uid = "123456789"
        not_ready_pod.status = not_ready_status
        not_ready_pod.metadata = not_ready_pod_metadata
        k8s_api.read_namespaced_pod = mock.MagicMock(
            side_effect=[not_ready_pod
                         for i in range(4)])

        self.assertRaises(
            exceptions.TimeoutException,
            self.scenario._create_v1pod, manifest)

    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_list_v1rcs(self, mock__get_k8s_api_client):
        k8s_api = mock__get_k8s_api_client.return_value
        self.scenario._list_v1rcs()
        (k8s_api.list_namespaced_replication_controller
            .assert_called_once_with(namespace="default"))
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.k8s_list_v1rcs")

    @mock.patch("random.choice")
    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_create_v1rc(self, mock__get_k8s_api_client,
                         mock_random_choice):
        k8s_api = mock__get_k8s_api_client.return_value
        manifest = (
            {"apiVersion": "v1",
             "kind": "ReplicationController",
             "metadata": {"name": "nginx-controller"},
             "spec": {"replicas": 2,
                      "selector": {"name": "nginx"},
                      "template": {"metadata":
                                   {"labels":
                                    {"name": "nginx"}}}}})
        suffix = "-"
        for i in range(5):
            suffix = suffix + mock_random_choice.return_value
        rcname = manifest["metadata"]["name"] + suffix
        rc = api_client.models.V1ReplicationController()
        rc.spec = api_client.models.V1ReplicationControllerSpec()
        rc.spec.replicas = manifest["spec"]["replicas"]
        k8s_api.create_namespaced_replication_controller.return_value = rc
        not_ready_rc = api_client.models.V1ReplicationController()
        not_ready_rc_status = (
            api_client.models.V1ReplicationControllerStatus(replicas=0))
        not_ready_rc.status = not_ready_rc_status
        ready_rc = api_client.models.V1ReplicationController()
        ready_rc_status = api_client.models.V1ReplicationControllerStatus(
            replicas=manifest["spec"]["replicas"]
        )
        ready_rc_metadata = api_client.models.V1ObjectMeta()
        ready_rc_metadata.uid = "123456789"
        ready_rc_metadata.name = rcname
        ready_rc.status = ready_rc_status
        ready_rc.metadata = ready_rc_metadata
        k8s_api.read_namespaced_replication_controller = mock.MagicMock(
            side_effect=[not_ready_rc, ready_rc])
        self.scenario._create_v1rc(manifest)
        (k8s_api.create_namespaced_replication_controller
            .assert_called_once_with(body=manifest, namespace="default"))
        (k8s_api.read_namespaced_replication_controller
            .assert_called_with(name=rcname, namespace="default"))
        self._test_atomic_action_timer(
            self.scenario.atomic_actions(), "magnum.k8s_create_v1rc")

    @mock.patch("time.time")
    @mock.patch("random.choice")
    @mock.patch(MAGNUM_UTILS + ".MagnumScenario._get_k8s_api_client")
    def test_create_v1rc_timeout(self, mock__get_k8s_api_client,
                                 mock_random_choice, mock_time):
        k8s_api = mock__get_k8s_api_client.return_value
        manifest = (
            {"apiVersion": "v1",
             "kind": "ReplicationController",
             "metadata": {"name": "nginx-controller"},
             "spec": {"replicas": 2,
                      "selector": {"app": "nginx"},
                      "template": {"metadata":
                                   {"labels":
                                    {"name": "nginx"}}}}})
        rc = api_client.models.V1ReplicationController()
        rc.spec = api_client.models.V1ReplicationControllerSpec()
        rc.spec.replicas = manifest["spec"]["replicas"]
        mock_time.side_effect = [1, 2, 3, 4, 5, 1800, 1801]
        k8s_api.create_namespaced_replication_controller.return_value = rc
        not_ready_rc = api_client.models.V1ReplicationController()
        not_ready_rc_status = (
            api_client.models.V1ReplicationControllerStatus(replicas=0))
        not_ready_rc_metadata = api_client.models.V1ObjectMeta()
        not_ready_rc_metadata.uid = "123456789"
        not_ready_rc.status = not_ready_rc_status
        not_ready_rc.metadata = not_ready_rc_metadata
        k8s_api.read_namespaced_replication_controller = mock.MagicMock(
            side_effect=[not_ready_rc
                         for i in range(4)])

        self.assertRaises(
            exceptions.TimeoutException,
            self.scenario._create_v1rc, manifest)
