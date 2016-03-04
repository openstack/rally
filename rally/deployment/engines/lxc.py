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

import os

import netaddr
import six

from rally.common.i18n import _
from rally.common import logging
from rally.common import objects
from rally.deployment import engine
from rally.deployment.serverprovider import provider
from rally.deployment.serverprovider.providers import lxc
from rally import exceptions

LOG = logging.getLogger(__name__)
START_SCRIPT = "start.sh"


def get_script_path(name):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        "lxc", name)


@engine.configure(name="LxcEngine")
class LxcEngine(engine.Engine):
    """Deploy with other engines in lxc containers.

    Sample configuration:

    .. code-block:: json

        {
            "type": "LxcEngine",
            "provider": {
                "type": "DummyProvider",
                "credentials": [{"user": "root", "host": "example.net"}]
            },
            "distribution": "ubuntu",
            "release": "raring",
            "tunnel_to": ["10.10.10.10", "10.10.10.11"],
            "start_lxc_network": "10.1.1.0/24",
            "container_name_prefix": "devstack-node",
            "containers_per_host": 16,
            "start_script": "~/start.sh",
            "engine": { ... }
        }
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "distribution": {"type": "string"},
            "release": {"type": "string"},
            "start_lxc_network": {"type": "string",
                                  "pattern": "^(\d+\.){3}\d+\/\d+$"},
            "containers_per_host": {"type": "integer"},
            "tunnel_to": {"type": "array",
                          "elements": {"type": "string",
                                       "pattern": "^(\d+\.){3}\d+$"}},
            "container_name": {"type": "string"},
            "provider": {"type": "object",
                         "properties": {"type": {"type": "string"}}},
        },
        "required": ["type", "containers_per_host", "container_name",
                     "provider"]
    }

    def validate(self):
        super(LxcEngine, self).validate()
        if "start_lxc_network" not in self.config:
            return
        lxc_net = netaddr.IPNetwork(self.config["start_lxc_network"])
        num_containers = self.config["containers_per_host"]
        if lxc_net.size - 3 < num_containers:
            message = _("Network size is not enough for %d hosts.")
            raise exceptions.InvalidConfigException(message % num_containers)

    def _deploy_first(self, lxc_host, name, distribution, release):
        lxc_host.prepare()
        lxc_host.create_container(name, distribution, release)
        lxc_host.start_containers()
        items = six.iteritems(
            lxc_host.get_server_object(name).get_credentials())
        # filter out all keys where value is None
        credentials = dict(filter(lambda x: x[1] is not None, items))
        engine_config = self.config["engine"].copy()
        engine_config["provider"] = {"type": "DummyProvider",
                                     "credentials": [credentials]}
        deployment = objects.Deployment(config=engine_config,
                                        parent_uuid=self.deployment["uuid"])
        deployer = engine.Engine.get_engine(engine_config["name"],
                                            deployment)
        deployer.deploy()
        lxc_host.stop_containers()

    def _get_provider(self):
        return provider.ProviderFactory.get_provider(self.config["provider"],
                                                     self.deployment)

    @logging.log_deploy_wrapper(LOG.info, _("Create containers on host"))
    def deploy(self):
        name = self.config["container_name"]
        start_script = self.config.get("start_script",
                                       get_script_path(START_SCRIPT))
        distribution = self.config["distribution"]
        release = self.config.get("release")
        network = self.config.get("start_lxc_network")
        if network:
            network = netaddr.IPNetwork(network)
        else:
            ip = "0"

        self.provider = self._get_provider()

        for server in self.provider.create_servers():
            config = {"tunnel_to": self.config.get("tunnel_to", [])}
            if network:
                config["network"] = str(network)
                ip = str(network.ip).replace(".", "-")
            else:
                ip = "0"
            name_prefix = "%s-%s" % (name, ip)
            first_name = name_prefix + "-000"
            lxc_host = lxc.LxcHost(server, config)
            self._deploy_first(lxc_host, first_name, distribution, release)
            for i in range(1, self.config["containers_per_host"]):
                clone_name = "%s-%03d" % (name_prefix, i)
                lxc_host.create_clone(clone_name, first_name)
            lxc_host.start_containers()
            info = {"host": server.get_credentials(),
                    "containers": lxc_host.containers,
                    "forwarded_ports": lxc_host._port_cache.items(),
                    "config": config}
            self.deployment.add_resource(provider_name="LxcEngine", info=info)
            for container in lxc_host.get_server_objects():
                container.ssh.run("/bin/sh -e", stdin=open(start_script, "rb"))
            if network:
                network += 1
        return {"admin": objects.Credential("", "", "", "")}

    def cleanup(self):
        resources = self.deployment.get_resources()
        for resource in resources:
            server = provider.Server.from_credentials(resource.info["host"])
            lxc_host = lxc.LxcHost(server, resource.info["config"])
            lxc_host.containers = resource.info["containers"]
            lxc_host.destroy_containers()
            lxc_host.destroy_ports(resource.info["forwarded_ports"])
            lxc_host.delete_tunnels()
            self.deployment.delete_resource(resource.id)
        self._get_provider().destroy_servers()
