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
import os
import subprocess
import sys

import six

from rally.cli import cliutils
from rally.common.plugin import discover
from rally import consts
from rally.plugins.openstack import credential


def skip_if_service(service):
    def wrapper(func):
        def inner(self):
            if service in self.clients.services().values():
                return []
            return func(self)
        return inner
    return wrapper


class ResourceManager(object):

    REQUIRED_SERVICE = None
    STR_ATTRS = ("id", "name")

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
            for raw_res in resources:
                res = {"cls": cls, "resource_name": resource_name,
                       "id": {}, "props": {}}
                if not isinstance(raw_res, dict):
                    raw_res = {k: getattr(raw_res, k) for k in dir(raw_res)
                               if not k.startswith("_")
                               if not callable(getattr(raw_res, k))}
                for key, value in raw_res.items():
                    if key.startswith("_"):
                        continue
                    if key in self.STR_ATTRS:
                        res["id"][key] = value
                    else:
                        try:
                            res["props"][key] = json.dumps(value, indent=2)
                        except TypeError:
                            res["props"][key] = str(value)
                if not res["id"] and not res["props"]:
                    print("1: %s" % raw_res)
                    print("2: %s" % cls)
                    print("3: %s" % resource_name)
                    raise ValueError("Failed to represent resource %r" %
                                     raw_res)
                all_resources.append(res)
        return all_resources


class Keystone(ResourceManager):

    REQUIRED_SERVICE = consts.Service.KEYSTONE

    def list_users(self):
        return self.client.users.list()

    def list_tenants(self):
        if hasattr(self.client, "projects"):
            return self.client.projects.list()  # V3
        return self.client.tenants.list()  # V2

    def list_roles(self):
        return self.client.roles.list()

    def list_ec2credentials(self):
        users = self.list_users()
        ec2_list = []
        for user in users:
            ec2_list.extend(
                self.client.ec2.list(user.id))
        return ec2_list


class Magnum(ResourceManager):

    REQUIRED_SERVICE = consts.Service.MAGNUM

    def list_cluster_templates(self):
        result = []
        marker = None
        while True:
            ct_list = self.client.cluster_templates.list(marker=marker)
            if not ct_list:
                break
            result.extend(ct_list)
            marker = ct_list[-1].uuid
        return result

    def list_clusters(self):
        result = []
        marker = None
        while True:
            clusters = self.client.clusters.list(marker=marker)
            if not clusters:
                break
            result.extend(clusters)
            marker = clusters[-1].uuid
        return result


class Mistral(ResourceManager):

    REQUIRED_SERVICE = consts.Service.MISTRAL

    def list_workbooks(self):
        return self.client.workbooks.list()

    def list_workflows(self):
        return self.client.workflows.list()

    def list_executions(self):
        return self.client.executions.list()


class Nova(ResourceManager):

    REQUIRED_SERVICE = consts.Service.NOVA

    def list_flavors(self):
        return self.client.flavors.list()

    def list_aggregates(self):
        return self.client.aggregates.list()

    def list_hypervisors(self):
        return self.client.hypervisors.list()

    def list_agents(self):
        return self.client.agents.list()

    def list_keypairs(self):
        return self.client.keypairs.list()

    def list_servers(self):
        return self.client.servers.list(
            search_opts={"all_tenants": True})

    def list_server_groups(self):
        return self.client.server_groups.list(all_projects=True)

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

    def list_bgpvpns(self):
        if self.has_extension("bgpvpn"):
            return self.client.list_bgpvpns()["bgpvpns"]


class Glance(ResourceManager):

    REQUIRED_SERVICE = consts.Service.GLANCE

    def list_images(self):
        return self.client.images.list()


class Heat(ResourceManager):

    REQUIRED_SERVICE = consts.Service.HEAT

    def list_resource_types(self):
        return self.client.resource_types.list()

    def list_stacks(self):
        return self.client.stacks.list()


class Cinder(ResourceManager):

    REQUIRED_SERVICE = consts.Service.CINDER

    def list_availability_zones(self):
        return self.client.availability_zones.list()

    def list_backups(self):
        return self.client.backups.list()

    def list_volume_snapshots(self):
        return self.client.volume_snapshots.list()

    def list_volume_types(self):
        return self.client.volume_types.list()

    def list_encryption_types(self):
        return self.client.volume_encryption_types.list()

    def list_transfers(self):
        return self.client.transfers.list()

    def list_volumes(self):
        return self.client.volumes.list(search_opts={"all_tenants": True})

    def list_qos(self):
        return self.client.qos_specs.list()


class Senlin(ResourceManager):

    REQUIRED_SERVICE = consts.Service.SENLIN

    def list_clusters(self):
        return self.client.clusters()

    def list_profiles(self):
        return self.client.profiles()


class Manila(ResourceManager):

    REQUIRED_SERVICE = consts.Service.MANILA

    def list_shares(self):
        return self.client.shares.list(detailed=False,
                                       search_opts={"all_tenants": True})

    def list_share_networks(self):
        return self.client.share_networks.list(
            detailed=False, search_opts={"all_tenants": True})

    def list_share_servers(self):
        return self.client.share_servers.list(
            search_opts={"all_tenants": True})


class Gnocchi(ResourceManager):

    REQUIRED_SERVICE = consts.Service.GNOCCHI

    def list_resources(self):
        return self.client.resource.list()


class Ironic(ResourceManager):

    REQUIRED_SERVICE = consts.Service.IRONIC

    def list_nodes(self):
        return self.client.node.list()


class Sahara(ResourceManager):

    REQUIRED_SERVICE = consts.Service.SAHARA

    def list_node_group_templates(self):
        return self.client.node_group_templates.list()


class Murano(ResourceManager):

    REQUIRED_SERVICE = consts.Service.MURANO

    def list_environments(self):
        return self.client.environments.list()

    def list_packages(self):
        return self.client.packages.list(include_disabled=True)


class Designate(ResourceManager):

    REQUIRED_SERVICE = consts.Service.DESIGNATE

    def list_domains(self):
        return self.client.domains.list()

    def list_records(self):
        result = []
        result.extend(self.client.records.list(domain_id)
                      for domain_id in self.client.domains.list())
        return result

    def list_servers(self):
        return self.client.servers.list()

    def list_zones(self):
        return self.clients.designate("2").zones.list()

    def list_recordset(self):
        client = self.clients.designate("2")
        results = []
        results.extend(client.recordsets.list(zone_id)
                       for zone_id in client.zones.list())
        return results


class Trove(ResourceManager):

    REQUIRED_SERVICE = consts.Service.TROVE

    def list_backups(self):
        return self.client.backup.list()

    def list_clusters(self):
        return self.client.cluster.list()

    def list_configurations(self):
        return self.client.configuration.list()

    def list_databases(self):
        return self.client.database.list()

    def list_datastore(self):
        return self.client.datastore.list()

    def list_instances(self):
        return self.client.list(include_clustered=True)

    def list_modules(self):
        return self.client.module.list(datastore="all")


class Monasca(ResourceManager):

    REQUIRED_SERVICE = consts.Service.MONASCA

    def list_metrics(self):
        return self.client.metrics.list()


class Watcher(ResourceManager):

    REQUIRED_SERVICE = consts.Service.WATCHER

    REPR_KEYS = ("uuid", "name")

    def list_audits(self):
        return self.client.audit.list()

    def list_audit_templates(self):
        return self.client.audit_template.list()

    def list_goals(self):
        return self.client.goal.list()

    def list_strategies(self):
        return self.client.strategy.list()

    def list_action_plans(self):
        return self.client.action_plan.list()


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
        self.clients = credential.OpenStackCredential(**kwargs).clients()

    def list(self):
        managers_classes = discover.itersubclasses(ResourceManager)
        resources = []
        for cls in managers_classes:
            manager = cls(self.clients)
            if manager.is_available():
                resources.extend(manager.get_resources())
        return resources

    def compare(self, with_list):
        def make_uuid(res):
            return"%s.%s:%s" % (
                res["cls"], res["resource_name"],
                ";".join(["%s=%s" % (k, v)
                          for k, v in sorted(res["id"].items())]))

        current_resources = dict((make_uuid(r), r) for r in self.list())
        saved_resources = dict((make_uuid(r), r) for r in with_list)

        removed = set(saved_resources.keys()) - set(current_resources.keys())
        removed = [saved_resources[k] for k in sorted(removed)]
        added = set(current_resources.keys()) - set(saved_resources.keys())
        added = [current_resources[k] for k in sorted(added)]

        return removed, added


def _print_tabular_resources(resources, table_label):
    def dict_formatter(d):
        return "\n".join("%s:%s" % (k, v) for k, v in d.items())

    cliutils.print_list(
        objs=[dict(r) for r in resources],
        fields=("cls", "resource_name", "id", "fields"),
        field_labels=("service", "resource type", "id", "fields"),
        table_label=table_label,
        formatters={"id": lambda d: dict_formatter(d["id"]),
                    "fields": lambda d: dict_formatter(d["props"])}
    )
    print("")


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
        out = subprocess.check_output(["rally", "deployment", "config",
                                       "--deployment", "devstack"])
        config = json.loads(out if six.PY2 else out.decode("utf-8"))
        config = config["openstack"]
        config.update(config.pop("admin"))
        if "users" in config:
            del config["users"]

    resources = CloudResources(**config)

    if args.dump_list:
        resources_list = resources.list()
        json.dump(resources_list, args.dump_list)
    elif args.compare_with_list:
        given_list = json.load(args.compare_with_list)
        changes = resources.compare(with_list=given_list)
        removed, added = changes

        # Cinder has a feature - cache images for speeding-up time of creating
        # volumes from images. let's put such cache-volumes into expected list
        volume_names = [
            "image-%s" % i["id"]["id"] for i in given_list
            if i["cls"] == "glance" and i["resource_name"] == "image"]

        # filter out expected additions
        expected = []
        for resource in added:
            if (
                    (resource["cls"] == "keystone" and
                     resource["resource_name"] == "role" and
                     resource["id"].get("name") == "_member_") or

                    (resource["cls"] == "neutron" and
                     resource["resource_name"] == "security_group" and
                     resource["id"].get("name") == "default") or

                    (resource["cls"] == "cinder" and
                     resource["resource_name"] == "volume" and
                     resource["id"].get("name") in volume_names) or

                    resource["cls"] == "murano" or

                    # Glance has issues with uWSGI integration...
                    resource["cls"] == "glance"):
                expected.append(resource)

        for resource in expected:
            added.remove(resource)

        if removed:
            _print_tabular_resources(removed, "Removed resources")

        if added:
            _print_tabular_resources(added, "Added resources (unexpected)")

        if expected:
            _print_tabular_resources(expected, "Added resources (expected)")

        if any(changes):
            # NOTE(andreykurilin): '1' return value will fail gate job. It is
            #     ok for changes to Rally project, but changes to other
            #     projects, which have rally job, should not be affected by
            #     this check, since in most cases resources are left due
            #     to wrong cleanup of a particular scenario.
            if os.environ.get("ZUUL_PROJECT") == "openstack/rally":
                return 1
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
