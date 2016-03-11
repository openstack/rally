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
import re
import time

import netaddr
import six
from six import moves

from rally.common.i18n import _
from rally.common import logging
from rally.deployment.serverprovider import provider
from rally import exceptions


LOG = logging.getLogger(__name__)
INET_ADDR_RE = re.compile(r" *inet ((\d+\.){3}\d+)\/\d+ .*")
IPT_PORT_TEMPLATE = ("iptables -t nat -{action} PREROUTING -d {host_ip}"
                     " -p tcp --syn --dport {port}"
                     " -j DNAT --to-destination {ip}:22")


def _get_script(filename):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           "lxc", filename))
    return open(path, "rb")


def _get_script_from_template(template_filename, **kwargs):
    template = _get_script(template_filename).read()
    return moves.StringIO(template.format(**kwargs))


class LxcHost(object):
    """Represent lxc enabled host."""

    def __init__(self, server, config):
        """Initialize LxcHost object.

        :param server:  Server object
        :param config:  dictionary with following key/values:
            network         ipv4 network for containers
            lxc_bridge      bridge interface name (default lxcbr0)
            tunnel_to       ip address for make tunnel to
            forward_ssh     use ssh port forwarding (do not use for
                            controller nodes)

        """
        self.config = config
        if "network" in config:
            self.network = netaddr.IPNetwork(config["network"])
        else:
            self.network = None
        self.server = server
        self.containers = []
        self.path = "/var/lib/lxc/"
        self._port_cache = {}

    def _get_updated_server(self, **kwargs):
        credentials = self.server.get_credentials()
        credentials.update(kwargs)
        return provider.Server.from_credentials(credentials)

    @property
    def backingstore(self):
        if not hasattr(self, "_backingstore"):
            code = self.server.ssh.execute("df -t btrfs %s" % self.path)[0]
            self._backingstore = "" if code else "btrfs"
        return self._backingstore

    def prepare(self):
        if self.network:
            dhcp_start = str(self.network.network + 2)
            dhcp_end = str(self.network.network + self.network.size - 2)
            dhcp_range = ",".join([dhcp_start, dhcp_end])
            values = {
                "USE_LXC_BRIDGE": "true",
                "LXC_BRIDGE": self.config.get("lxc_bridge", "lxcbr0"),
                "LXC_ADDR": self.network.network + 1,
                "LXC_NETMASK": self.network.netmask,
                "LXC_NETWORK": self.network,
                "LXC_DHCP_RANGE": dhcp_range,
                "LXC_DHCP_MAX": self.network.size - 3,
            }
            config = moves.StringIO()
            for name, value in six.iteritems(values):
                config.write("%(name)s=\"%(value)s\"\n" % {"name": name,
                                                           "value": value})
            config.seek(0)
            self.server.ssh.run("cat > /tmp/.lxc_default", stdin=config)

        self.server.ssh.run("/bin/sh", stdin=_get_script("lxc-install.sh"))
        self.create_local_tunnels()
        self.create_remote_tunnels()

    def create_local_tunnels(self):
        """Create tunnel on lxc host side."""
        for tunnel_to in self.config["tunnel_to"]:
            script = _get_script_from_template("tunnel-local.sh",
                                               net=self.network,
                                               local=self.server.host,
                                               remote=tunnel_to)
            self.server.ssh.run("/bin/sh", stdin=script)

    def create_remote_tunnels(self):
        """Create tunnel on remote side."""
        for tunnel_to in self.config["tunnel_to"]:
            script = _get_script_from_template("tunnel-remote.sh",
                                               net=self.network,
                                               local=tunnel_to,
                                               remote=self.server.host)
            server = self._get_updated_server(host=tunnel_to)
            server.ssh.run("/bin/sh", stdin=script)

    def delete_tunnels(self):
        for tunnel_to in self.config["tunnel_to"]:
            remote_server = self._get_updated_server(host=tunnel_to)
            remote_server.ssh.execute("ip tun del t%s" % self.network.ip)
            self.server.ssh.execute("ip tun del t%s" % tunnel_to)

    def get_ip(self, name):
        """Get container's ip by name."""
        cmd = "lxc-attach -n %s ip addr list dev eth0" % name
        for attempt in range(1, 16):
            code, stdout = self.server.ssh.execute(cmd)[:2]
            if code:
                continue
            for line in stdout.splitlines():
                m = INET_ADDR_RE.match(line)
                if m:
                    return m.group(1)
            time.sleep(attempt)
        msg = _("Timeout waiting for ip address of container \"%s\"") % name
        raise exceptions.TimeoutException(msg)

    def get_port(self, ip):
        """Get forwarded ssh port for instance ip.

        Ssh port forwarding is used for containers access from outside.
        Any container is accessible by host's ip and forwarded port. E.g:

         6.6.6.6:10023 -> 10.1.1.11:22
         6.6.6.6:10024 -> 10.1.1.12:22
         6.6.6.6:10025 -> 10.1.1.13:22

        where 6.6.6.6 is host's ip.

        Ip->port association is stored in self._port_cache to reduce number
        of iptables calls.
        """
        if not self._port_cache:
            self._port_cache = {}
            port_re = re.compile(r".+ tcp dpt:(\d+).*to:([\d\.]+)\:22")
            cmd = "iptables -n -t nat -L PREROUTING"
            code, out, err = self.server.ssh.execute(cmd)
            for l in out:
                m = port_re.match(l)
                if m:
                    self._port_cache[m.group(2)] = int(m.group(1))
        port = self._port_cache.get(ip)

        if port is None:
            if self._port_cache:
                port = max(self._port_cache.values()) + 1
            else:
                port = 1222
        self._port_cache[ip] = port
        cmd = IPT_PORT_TEMPLATE.format(host_ip=self.server.host, ip=ip,
                                       port=port, action="I")
        self.server.ssh.run(cmd)
        return port

    def create_container(self, name, distribution, release=None):
        cmd = ["lxc-create"]
        if self.backingstore == "btrfs":
            cmd += ["-B", "btrfs"]
        cmd += ["-n", name, "-t", distribution]
        if release:
            if distribution == "ubuntu":
                cmd += ["--", "-r", release]
            elif distribution == "debian":
                cmd = ["SUITE=%s" % release] + cmd
        self.server.ssh.run(" ".join(cmd))
        self.configure_container(name)
        self.containers.append(name)

    def create_clone(self, name, source):
        cmd = ["lxc-clone"]

        if self.backingstore == "btrfs":
            cmd.append("--snapshot")
        cmd.extend(["-o", source, "-n", name])
        self.server.ssh.execute(" ".join(cmd))
        self.configure_container(name)
        self.containers.append(name)

    def configure_container(self, name):
        path = os.path.join(self.path, name, "rootfs")
        conf_script = _get_script("configure_container.sh")
        self.server.ssh.run("/bin/sh -e -s %s" % path, stdin=conf_script)

    def start_containers(self):
        for name in self.containers:
            self.server.ssh.run("lxc-start -d -n %s" % name)

    def stop_containers(self):
        for name in self.containers:
            self.server.ssh.run("lxc-stop -n %s" % name)

    def destroy_ports(self, ipports):
        script = ""
        for ip, port in ipports:
            cmd = IPT_PORT_TEMPLATE.format(action="D", port=port, ip=ip,
                                           host_ip=self.server.host)
            script += cmd + "\n"
        self.server.ssh.run("/bin/sh -e", stdin=script)

    def destroy_containers(self):
        for name in self.containers:
            self.server.ssh.run("lxc-stop -n %s" % name)
            self.server.ssh.run("lxc-destroy -n %s" % name)

    def get_server_object(self, name, wait=True):
        """Create Server object for container."""
        ip = self.get_ip(name)
        if self.config.get("forward_ssh", False):
            server = self._get_updated_server(port=self.get_port(ip))
        else:
            server = self._get_updated_server(host=ip)
        if wait:
            server.ssh.wait(timeout=300)
        return server

    def get_server_objects(self, wait=True):
        """Generate Server objects from all containers."""
        for name in self.containers:
            yield self.get_server_object(name, wait)


@provider.configure(name="LxcProvider")
class LxcProvider(provider.ProviderFactory):
    """Provide lxc container(s) on given host.

    Sample configuration:

    .. code-block:: json

        {
            "type": "LxcProvider",
            "distribution": "ubuntu",
            "start_lxc_network": "10.1.1.0/24",
            "containers_per_host": 32,
            "tunnel_to": ["10.10.10.10"],
            "forward_ssh": false,
            "container_name_prefix": "rally-multinode-02",
            "host_provider": {
                "type": "ExistingServers",
                "credentials": [{"user": "root", "host": "host.net"}]
            }
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
            "forward_ssh": {"type": "boolean"},
            "tunnel_to": {"type": "array",
                          "elements": {"type": "string",
                                       "pattern": "^(\d+\.){3}\d+$"}},
            "container_name_prefix": {"type": "string"},
            "host_provider": {"type": "object",
                              "properties": {"type": {"type": "string"}}},
        },
        "required": ["type", "containers_per_host",
                     "container_name_prefix", "host_provider"],

    }

    def validate(self):
        super(LxcProvider, self).validate()
        if "start_lxc_network" not in self.config:
            return
        lxc_net = netaddr.IPNetwork(self.config["start_lxc_network"])
        num_containers = self.config["containers_per_host"]
        if lxc_net.size - 3 < num_containers:
            message = _("Network size is not enough for %d hosts.")
            raise exceptions.InvalidConfigException(message % num_containers)

    def get_host_provider(self):
        return provider.ProviderFactory.get_provider(
            self.config["host_provider"], self.deployment)

    @logging.log_deploy_wrapper(LOG.info, _("Create containers on host"))
    def create_servers(self):
        host_provider = self.get_host_provider()
        name_prefix = self.config["container_name_prefix"]
        hosts = []
        if "start_lxc_network" in self.config:
            network = netaddr.IPNetwork(self.config["start_lxc_network"])
        else:
            network = None
        distribution = self.config.get("distribution", "ubuntu")
        release = self.config.get("release")

        for server in host_provider.create_servers():
            config = {"tunnel_to": self.config.get("tunnel_to", []),
                      "forward_ssh": self.config.get("forward_ssh", False)}
            if network:
                config["network"] = str(network)
            host = LxcHost(server, config)
            host.prepare()
            ip = str(network.ip).replace(".", "-") if network else "0"
            first_name = "%s-000-%s" % (name_prefix, ip)

            host.create_container(first_name, distribution, release)
            for i in range(1, self.config.get("containers_per_host", 1)):
                name = "%s-%03d-%s" % (name_prefix, i, ip)
                host.create_clone(name, first_name)
            host.start_containers()
            hosts.append(host)

            if network:
                network += 1

        servers = []

        for host in hosts:
            for server in host.get_server_objects():
                servers.append(server)
            info = {"host": host.server.get_credentials(),
                    "config": host.config,
                    "forwarded_ports": host._port_cache.items(),
                    "container_names": host.containers}
            self.resources.create(info)
        return servers

    @logging.log_deploy_wrapper(LOG.info, _("Destroy host(s)"))
    def destroy_servers(self):
        for resource in self.resources.get_all():
            server = provider.Server.from_credentials(resource["info"]["host"])
            lxc_host = LxcHost(server, resource["info"]["config"])
            lxc_host.containers = resource["info"]["container_names"]
            lxc_host.destroy_containers()
            lxc_host.destroy_ports(resource["info"]["forwarded_ports"])
            lxc_host.delete_tunnels()
            self.resources.delete(resource["id"])
        host_provider = self.get_host_provider()
        host_provider.destroy_servers()
