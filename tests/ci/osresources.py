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


"""List and compare most used OpenStack cloud resources."""


import argparse
import json
import subprocess
import sys

from rally.common.plugin import discover
from rally import consts
from rally import osclients


class ResourceManager(object):

    REQUIRED_SERVICE = None
    REPR_KEYS = ("id", "name", "tenant_id", "zone", "zoneName", "pool")

    def __init__(self, clients):
        self.clients = clients

    def is_available(self):
        if self.REQUIRED_SERVICE:
            return self.REQUIRED_SERVICE in self.clients.services().values()
        return True

    @property
    def client(self):
        return getattr(self.clients, self.__class__.__name__.lower())()

    def get_resources(self):
        all_resources = []
        cls = self.__class__.__name__.lower()
        for prop in dir(self):
            if not prop.startswith("list_"):
                continue
            f = getattr(self, prop)
            resources = f() or []
            resource_name = prop[5:][:-1]

            for res in resources:
                res_repr = []
                for key in self.REPR_KEYS + (resource_name,):
                    if isinstance(res, dict):
                        value = res.get(key)
                    else:
                        value = getattr(res, key, None)
                    if value:
                        res_repr.append("%s:%s" % (key, value))
                if not res_repr:
                    raise ValueError("Failed to represent resource %r" % res)

                all_resources.append(
                    "%s %s %s" % (cls, resource_name, " ".join(res_repr)))
        return all_resources


class Keystone(ResourceManager):

    def list_users(self):
        return self.client.users.list()

    def list_tenants(self):
        return self.client.tenants.list()

    def list_roles(self):
        return self.client.roles.list()


class Nova(ResourceManager):

    def list_flavors(self):
        return self.client.flavors.list()

    def list_floating_ip_pools(self):
        return self.client.floating_ip_pools.list()

    def list_floating_ips(self):
        return self.client.floating_ips.list()

    def list_images(self):
        return self.client.images.list()

    def list_keypairs(self):
        return self.client.keypairs.list()

    def list_networks(self):
        return self.client.networks.list()

    def list_security_groups(self):
        return self.client.security_groups.list(
            search_opts={"all_tenants": True})

    def list_servers(self):
        return self.client.servers.list(
            search_opts={"all_tenants": True})

    def list_services(self):
        return self.client.services.list()

    def list_availability_zones(self):
        return self.client.availability_zones.list()


class Neutron(ResourceManager):

    REQUIRED_SERVICE = consts.Service.NEUTRON

    def has_extension(self, name):
        extensions = self.client.list_extensions().get("extensions", [])
        return any(ext.get("alias") == name for ext in extensions)

    def list_networks(self):
        return self.client.list_networks()["networks"]

    def list_subnets(self):
        return self.client.list_subnets()["subnets"]

    def list_routers(self):
        return self.client.list_routers()["routers"]

    def list_ports(self):
        return self.client.list_ports()["ports"]

    def list_floatingips(self):
        return self.client.list_floatingips()["floatingips"]

    def list_security_groups(self):
        return self.client.list_security_groups()["security_groups"]

    def list_health_monitors(self):
        if self.has_extension("lbaas"):
            return self.client.list_health_monitors()["health_monitors"]

    def list_pools(self):
        if self.has_extension("lbaas"):
            return self.client.list_pools()["pools"]

    def list_vips(self):
        if self.has_extension("lbaas"):
            return self.client.list_vips()["vips"]


class Glance(ResourceManager):

    def list_images(self):
        return self.client.images.list()


class Heat(ResourceManager):

    REQUIRED_SERVICE = consts.Service.HEAT

    def list_resource_types(self):
        return self.client.resource_types.list()

    def list_stacks(self):
        return self.client.stacks.list()


class Cinder(ResourceManager):

    def list_availability_zones(self):
        return self.client.availability_zones.list()

    def list_backups(self):
        return self.client.backups.list()

    def list_volume_snapshots(self):
        return self.client.volume_snapshots.list()

    def list_volume_types(self):
        return self.client.volume_types.list()

    def list_volumes(self):
        return self.client.volumes.list(
            search_opts={"all_tenants": True})


class CloudResources(object):
    """List and compare cloud resources.

    resources = CloudResources(auth_url=..., ...)
    saved_list = resources.list()

    # Do something with the cloud ...

    changes = resources.compare(saved_list)
    has_changed = any(changes)
    removed, added = changes
    """

    def __init__(self, **kwargs):
        endpoint = osclients.objects.Endpoint(**kwargs)
        self.clients = osclients.Clients(endpoint)

    def _deduplicate(self, lst):
        """Change list duplicates to make all items unique.

        >>> resources._deduplicate(["a", "b", "c", "b", "b"])
        >>> ['a', 'b', 'c', 'b (duplicate 1)', 'b (duplicate 2)'
        """
        deduplicated_list = []
        for value in lst:
            if value in deduplicated_list:
                ctr = 0
                try_value = value
                while try_value in deduplicated_list:
                    ctr += 1
                    try_value = "%s (duplicate %i)" % (value, ctr)
                value = try_value
            deduplicated_list.append(value)
        return deduplicated_list

    def list(self):
        managers_classes = discover.itersubclasses(ResourceManager)
        resources = []
        for cls in managers_classes:
            manager = cls(self.clients)
            if manager.is_available():
                resources.extend(manager.get_resources())
        return sorted(self._deduplicate(resources))

    def compare(self, with_list):
        saved_resources = set(with_list)
        current_resources = set(self.list())
        removed = saved_resources - current_resources
        added = current_resources - saved_resources

        return sorted(list(removed)), sorted(list(added))


def main():

    parser = argparse.ArgumentParser(
        description=("Save list of OpenStack cloud resources or compare "
                     "with previously saved list."))
    parser.add_argument("--credentials",
                        type=argparse.FileType("r"),
                        metavar="<path/to/credentials.json>",
                        help="cloud credentials in JSON format")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dump-list",
                       type=argparse.FileType("w"),
                       metavar="<path/to/output/list.json>",
                       help="dump resources to given file in JSON format")
    group.add_argument("--compare-with-list",
                       type=argparse.FileType("r"),
                       metavar="<path/to/existent/list.json>",
                       help=("compare current resources with a list from "
                             "given JSON file"))
    args = parser.parse_args()

    if args.credentials:
        config = json.load(args.credentials)
    else:
        config = json.loads(subprocess.check_output(["rally", "deployment",
                                                     "config"]))
        config.update(config.pop("admin"))
        del config["type"]

    resources = CloudResources(**config)

    if args.dump_list:
        resources_list = resources.list()
        json.dump(resources_list, args.dump_list, indent=2)
    elif args.compare_with_list:
        given_list = json.load(args.compare_with_list)
        changes = resources.compare(with_list=given_list)
        removed, added = changes
        sys.stdout.write(
            json.dumps({"removed": removed, "added": added}, indent=2))
        if any(changes):
            return 0  # `1' will fail gate job
    return 0


if __name__ == "__main__":
    sys.exit(main())
