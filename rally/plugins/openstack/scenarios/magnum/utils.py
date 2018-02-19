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
import random
import string
import time

from kubernetes import client as k8s_config
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api
from kubernetes.client.rest import ApiException

from rally.common import cfg
from rally.common import utils as common_utils
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF


class MagnumScenario(scenario.OpenStackScenario):
    """Base class for Magnum scenarios with basic atomic actions."""

    @atomic.action_timer("magnum.list_cluster_templates")
    def _list_cluster_templates(self, **kwargs):
        """Return list of cluster_templates.

        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of cluster_templates to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for cluster_templates
                       listing

        :returns: cluster_templates list
        """

        return self.clients("magnum").cluster_templates.list(**kwargs)

    @atomic.action_timer("magnum.create_cluster_template")
    def _create_cluster_template(self, **kwargs):
        """Create a cluster_template

        :param kwargs: optional additional arguments for cluster_template
                       creation
        :returns: magnum cluster_template
        """

        kwargs["name"] = self.generate_random_name()

        return self.clients("magnum").cluster_templates.create(**kwargs)

    @atomic.action_timer("magnum.get_cluster_template")
    def _get_cluster_template(self, cluster_template):
        """Return details of the specify cluster template.

        :param cluster_template: ID or name of the cluster template to show
        :returns: clustertemplate detail
        """
        return self.clients("magnum").cluster_templates.get(cluster_template)

    @atomic.action_timer("magnum.list_clusters")
    def _list_clusters(self, limit=None, **kwargs):
        """Return list of clusters.

        :param limit: Optional, the maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of clusters to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for clusters listing

        :returns: clusters list
        """
        return self.clients("magnum").clusters.list(limit=limit, **kwargs)

    @atomic.action_timer("magnum.create_cluster")
    def _create_cluster(self, cluster_template, node_count, **kwargs):
        """Create a cluster

        :param cluster_template: cluster_template for the cluster
        :param node_count: the cluster node count
        :param kwargs: optional additional arguments for cluster creation
        :returns: magnum cluster
        """

        name = self.generate_random_name()
        cluster = self.clients("magnum").clusters.create(
            name=name, cluster_template_id=cluster_template,
            node_count=node_count, **kwargs)

        common_utils.interruptable_sleep(
            CONF.openstack.magnum_cluster_create_prepoll_delay)
        cluster = utils.wait_for_status(
            cluster,
            ready_statuses=["CREATE_COMPLETE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.openstack.magnum_cluster_create_timeout,
            check_interval=CONF.openstack.magnum_cluster_create_poll_interval,
            id_attr="uuid"
        )
        return cluster

    @atomic.action_timer("magnum.get_cluster")
    def _get_cluster(self, cluster):
        """Return details of the specify cluster.

        :param cluster: ID or name of the cluster to show
        :returns: cluster detail
        """
        return self.clients("magnum").clusters.get(cluster)

    @atomic.action_timer("magnum.get_ca_certificate")
    def _get_ca_certificate(self, cluster_uuid):
        """Get CA certificate for this cluster

        :param cluster_uuid: uuid of the cluster
        """
        return self.clients("magnum").certificates.get(cluster_uuid)

    @atomic.action_timer("magnum.create_ca_certificate")
    def _create_ca_certificate(self, csr_req):
        """Send csr to Magnum to have it signed

        :param csr_req: {"cluster_uuid": <uuid>, "csr": <csr file content>}
        """
        return self.clients("magnum").certificates.create(**csr_req)

    def _get_k8s_api_client(self):
        cluster_uuid = self.context["tenant"]["cluster"]
        cluster = self._get_cluster(cluster_uuid)
        cluster_template = self._get_cluster_template(
            cluster.cluster_template_id)
        key_file = None
        cert_file = None
        ca_certs = None
        if not cluster_template.tls_disabled:
            dir = self.context["ca_certs_directory"]
            key_file = cluster_uuid + ".key"
            key_file = os.path.join(dir, key_file)
            cert_file = cluster_uuid + ".crt"
            cert_file = os.path.join(dir, cert_file)
            ca_certs = cluster_uuid + "_ca.crt"
            ca_certs = os.path.join(dir, ca_certs)
        if hasattr(k8s_config, "ConfigurationObject"):
            # k8sclient < 4.0.0
            config = k8s_config.ConfigurationObject()
        else:
            config = k8s_config.Configuration()
        config.host = cluster.api_address
        config.ssl_ca_cert = ca_certs
        config.cert_file = cert_file
        config.key_file = key_file
        client = api_client.ApiClient(config=config)
        return core_v1_api.CoreV1Api(client)

    @atomic.action_timer("magnum.k8s_list_v1pods")
    def _list_v1pods(self):
        """List all pods.

        """
        k8s_api = self._get_k8s_api_client()
        return k8s_api.list_node(namespace="default")

    @atomic.action_timer("magnum.k8s_create_v1pod")
    def _create_v1pod(self, manifest):
        """Create a pod on the specify cluster.

        :param manifest: manifest use to create the pod
        """
        k8s_api = self._get_k8s_api_client()
        podname = manifest["metadata"]["name"] + "-"
        for i in range(5):
            podname = podname + random.choice(string.ascii_lowercase)
        manifest["metadata"]["name"] = podname

        for i in range(150):
            try:
                k8s_api.create_namespaced_pod(body=manifest,
                                              namespace="default")
                break
            except ApiException as e:
                if e.status != 403:
                    raise
            time.sleep(2)

        start = time.time()
        while True:
            resp = k8s_api.read_namespaced_pod(
                name=podname, namespace="default")

            if resp.status.conditions:
                for condition in resp.status.conditions:
                    if condition.type.lower() == "ready" and \
                       condition.status.lower() == "true":
                        return resp

            if (time.time() - start > CONF.openstack.k8s_pod_create_timeout):
                raise exceptions.TimeoutException(
                    desired_status="Ready",
                    resource_name=podname,
                    resource_type="Pod",
                    resource_id=resp.metadata.uid,
                    resource_status=resp.status,
                    timeout=CONF.openstack.k8s_pod_create_timeout)
            common_utils.interruptable_sleep(
                CONF.openstack.k8s_pod_create_poll_interval)

    @atomic.action_timer("magnum.k8s_list_v1rcs")
    def _list_v1rcs(self):
        """List all rcs.

        """
        k8s_api = self._get_k8s_api_client()
        return k8s_api.list_namespaced_replication_controller(
            namespace="default")

    @atomic.action_timer("magnum.k8s_create_v1rc")
    def _create_v1rc(self, manifest):
        """Create rc on the specify cluster.

        :param manifest: manifest use to create the replication controller
        """
        k8s_api = self._get_k8s_api_client()
        suffix = "-"
        for i in range(5):
            suffix = suffix + random.choice(string.ascii_lowercase)
        rcname = manifest["metadata"]["name"] + suffix
        manifest["metadata"]["name"] = rcname
        resp = k8s_api.create_namespaced_replication_controller(
            body=manifest,
            namespace="default")
        expectd_status = resp.spec.replicas
        start = time.time()
        while True:
            resp = k8s_api.read_namespaced_replication_controller(
                name=rcname,
                namespace="default")
            status = resp.status.replicas
            if status == expectd_status:
                return resp
            else:
                if time.time() - start > CONF.openstack.k8s_rc_create_timeout:
                    raise exceptions.TimeoutException(
                        desired_status=expectd_status,
                        resource_name=rcname,
                        resource_type="ReplicationController",
                        resource_id=resp.metadata.uid,
                        resource_status=status,
                        timeout=CONF.openstack.k8s_rc_create_timeout)
                common_utils.interruptable_sleep(
                    CONF.openstack.k8s_rc_create_poll_interval)
