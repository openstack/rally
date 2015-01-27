# Copyright 2013: Mirantis Inc.
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

import json
import re
import time

import requests

from rally.common import log as logging

LOG = logging.getLogger(__name__)

FILTER_REG = re.compile(r"^([a-z]+)\s*([<>=!]=|<|>)\s*(.+)$")
INT_REG = re.compile(r"^(\d+)(K|M|G|T)?$")


class FuelException(Exception):
    pass


class FuelClientException(FuelException):

    def __init__(self, code, body):
        self.code = code
        self.body = body

    def __str__(self):
        return ("FuelClientException. "
                "Code: %(code)d Body: %(body)s" % {"code": self.code,
                                                   "body": self.body})


class FuelNetworkVerificationFailed(FuelException):
    pass


class FuelNode(object):

    def __init__(self, node):
        self.node = node
        self.ATTRIBUTE_MAP = {
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "<=": lambda x, y: x <= y,
            ">=": lambda x, y: x >= y,
            "<": lambda x, y: x < y,
            ">": lambda x, y: x > y,
        }
        self.FACTOR_MAP = {
            "K": 1024,
            "M": 1048576,
            "G": 1073741824,
            "T": 1099511627776,
            None: 1,
        }

    def __getitem__(self, key):
        return self.node[key]

    def check_filters(self, filters):
        return all((self.check(f) for f in filters))

    def check(self, filter_string):
        if self.node["cluster"] is not None:
            return False
        m = FILTER_REG.match(filter_string)
        if m is None:
            raise ValueError("Invalid filter: %s" % filter_string)
        attribute, operator, value = m.groups()
        return self._check(attribute, value, operator)

    def _check(self, attribute, value, operator):
        attribute = getattr(self, "_get_" + attribute)()
        checker = self.ATTRIBUTE_MAP[operator]
        m = INT_REG.match(value)
        if m:
            value = int(m.group(1)) * self.FACTOR_MAP[m.group(2)]
        return checker(attribute, value)

    def _get_ram(self):
        return self.node["meta"]["memory"]["total"]

    def _get_mac(self):
        return self.node["mac"]

    def _get_storage(self):
        return sum((d["size"] for d in self.node["meta"]["disks"]))

    def _get_cpus(self):
        return self.node["meta"]["cpu"]["total"]


class FuelCluster(object):

    def __init__(self, client, **config):
        """Create Fuel cluster.

        :param client:              FuelClient instance.
        :param name:                Name
        :param release:             Release id. Integer.
        :param mode:                One of multinode, ha_compact
        :param net_provider:        One of nova_network, neutron
        :param net_segment_type:    One of gre, vlan.
        :param dns_nameservers:     List of strings.
        """

        self.client = client
        self.cluster = client.post("clusters", config)

    def get_nodes(self):
        return self.client.get("nodes?cluster_id=%d" % self.cluster["id"])

    def set_nodes(self, nodes, roles):
        if not nodes:
            return
        node_list = []
        for n in nodes:
            node_list.append({"id": n["id"],
                              "pending_roles": roles,
                              "pending_addition": True,
                              "cluster_id": self.cluster["id"]})
        self.client.put("nodes", node_list)

    def configure_network(self, config):
        netconfig = self.get_network()
        for network in netconfig["networks"]:
            if network["name"] in config:
                network.update(config[network["name"]])
        self.set_network(netconfig)

    def deploy(self):
        self.client.put("clusters/%d/changes" % self.cluster["id"], {})
        for task in self.client.get_tasks(self.cluster["id"]):
            if task["name"] == "deploy":
                task_id = task["id"]
                break
        while 1:
            time.sleep(10)
            task = self.client.get_task(task_id)
            if task["progress"] == 100:
                return
            LOG.info("Deployment in progress. %d%% done." % task["progress"])

    def get_network(self):
        args = {"cluster_id": self.cluster["id"],
                "net_provider": self.cluster["net_provider"]}
        url = ("clusters/%(cluster_id)d/network_configuration/"
               "%(net_provider)s" % args)
        return self.client.get(url)

    def set_network(self, config):
        self.verify_network(config)
        args = {"cluster_id": self.cluster["id"],
                "net_provider": self.cluster["net_provider"]}
        url = ("clusters/%(cluster_id)d/network_configuration/"
               "%(net_provider)s" % args)
        self.client.put(url, config)

    def verify_network(self, config):
        args = {"cluster_id": self.cluster["id"],
                "net_provider": self.cluster["net_provider"]}
        url = ("clusters/%(cluster_id)d/network_configuration/"
               "%(net_provider)s/verify" % args)
        task_id = self.client.put(url, config)["id"]
        while 1:
            time.sleep(5)
            task = self.client.get_task(task_id)
            if task["progress"] == 100:
                if task["message"]:
                    raise FuelNetworkVerificationFailed(task["message"])
                else:
                    return
            LOG.info("Network verification in progress."
                     " %d%% done." % task["progress"])

    def get_attributes(self):
        return self.client.get("clusters/%d/attributes" % self.cluster["id"])

    def get_endpoint_ip(self):
        if self.cluster["mode"].startswith("ha_"):
            netdata = self.get_network()
            return netdata["public_vip"]

        for node in self.get_nodes():
            if "controller" in node["roles"]:
                for net in node["network_data"]:
                    if net["name"] == "public":
                        return net["ip"].split("/")[0]

        raise FuelException("Unable to get endpoint ip.")


class FuelNodesCollection(object):
    nodes = []

    def __init__(self, nodes):
        for node in nodes:
            self.nodes.append(FuelNode(node))

    def pop(self, filters):
        for i, node in enumerate(self.nodes):
            if node.check_filters(filters):
                return self.nodes.pop(i)


class FuelClient(object):

    def __init__(self, base_url):
        self.base_url = base_url

    def _request(self, method, url, data=None):
        if data:
            data = json.dumps(data)
        headers = {"content-type": "application/json"}
        reply = getattr(requests, method)(self.base_url + url, data=data,
                                          headers=headers)
        if reply.status_code >= 300 or reply.status_code < 200:
            raise FuelClientException(code=reply.status_code, body=reply.text)
        if reply.text and reply.headers["content-type"] == "application/json":
            return json.loads(reply.text)
        return reply

    def get(self, url):
        return self._request("get", url)

    def post(self, url, data):
        return self._request("post", url, data)

    def put(self, url, data):
        return self._request("put", url, data)

    def delete(self, url):
        return self._request("delete", url)

    def get_releases(self):
        return self.get("releases")

    def get_task(self, task_id):
        return self.get("tasks/%d" % task_id)

    def get_tasks(self, cluster_id):
        return self.get("tasks?cluster_id=%d" % cluster_id)

    def get_node(self, node_id):
        return self.get("nodes/%d" % node_id)

    def get_nodes(self):
        return FuelNodesCollection(self.get("nodes"))

    def delete_cluster(self, cluster_id):
        self.delete("clusters/%s" % cluster_id)
