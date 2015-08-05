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

import six

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import objects
from rally.common import utils
from rally import consts
from rally.deployment import engine
from rally.deployment.serverprovider import provider


LOG = logging.getLogger(__name__)
DEVSTACK_REPO = "https://git.openstack.org/openstack-dev/devstack"
DEVSTACK_BRANCH = "master"
DEVSTACK_USER = "rally"


def get_script(name):
    return open(os.path.join(os.path.abspath(
        os.path.dirname(__file__)), "devstack", name), "rb")


def get_updated_server(server, **kwargs):
    credentials = server.get_credentials()
    credentials.update(kwargs)
    return provider.Server.from_credentials(credentials)


@engine.configure(name="DevstackEngine")
class DevstackEngine(engine.Engine):
    """Deploy Devstack cloud.

    Sample configuration:

        {
            "type": "DevstackEngine",
            "devstack_repo": "https://example.com/devstack/",
            "localrc": {
                "ADMIN_PASSWORD": "secret"
            },
            "provider": {
                "type": "ExistingServers",
                "credentials": [{"user": "root", "host": "10.2.0.8"}]
            }
        }
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "provider": {"type": "object"},
            "localrc": {"type": "object"},
            "devstack_repo": {"type": "string"},
            "devstack_branch": {"type": "string"},
        },
        "required": ["type", "provider"]
    }

    def __init__(self, deployment):
        super(DevstackEngine, self).__init__(deployment)
        self.localrc = {
            "DATABASE_PASSWORD": "rally",
            "RABBIT_PASSWORD": "rally",
            "SERVICE_TOKEN": "rally",
            "SERVICE_PASSWORD": "rally",
            "ADMIN_PASSWORD": "admin",
            "RECLONE": "yes",
            "SYSLOG": "yes",
        }
        if "localrc" in self.config:
            self.localrc.update(self.config["localrc"])

    @utils.log_deploy_wrapper(LOG.info, _("Prepare server for devstack"))
    def prepare_server(self, server):
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                   "devstack", "install.sh"))
        server.ssh.run("/bin/sh -e", stdin=open(script_path, "rb"))
        if server.password:
            server.ssh.run("chpasswd", stdin="rally:%s" % server.password)

    @utils.log_deploy_wrapper(LOG.info, _("Deploy devstack"))
    def deploy(self):
        self.servers = self.get_provider().create_servers()
        devstack_repo = self.config.get("devstack_repo", DEVSTACK_REPO)
        devstack_branch = self.config.get("devstack_branch", DEVSTACK_BRANCH)
        localrc = ""
        for k, v in six.iteritems(self.localrc):
            localrc += "%s=%s\n" % (k, v)

        for server in self.servers:
            self.deployment.add_resource(provider_name="DevstackEngine",
                                         type="credentials",
                                         info=server.get_credentials())
            cmd = "/bin/sh -e -s %s %s" % (devstack_repo, devstack_branch)
            server.ssh.run(cmd, stdin=get_script("install.sh"))
            devstack_server = get_updated_server(server, user=DEVSTACK_USER)
            devstack_server.ssh.run("cat > ~/devstack/localrc", stdin=localrc)
            devstack_server.ssh.run("~/devstack/stack.sh")

        admin_endpoint = objects.Endpoint("http://%s:5000/v2.0/" %
                                          self.servers[0].host, "admin",
                                          self.localrc["ADMIN_PASSWORD"],
                                          "admin",
                                          consts.EndpointPermission.ADMIN)
        return {"admin": admin_endpoint}

    def cleanup(self):
        for resource in self.deployment.get_resources(type="credentials"):
            server = provider.Server.from_credentials(resource.info)
            devstack_server = get_updated_server(server, user=DEVSTACK_USER)
            devstack_server.ssh.run("~/devstack/unstack.sh")
            self.deployment.delete_resource(resource.id)
