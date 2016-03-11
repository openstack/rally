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
import subprocess
import time
import uuid

import netaddr

from rally.deployment.serverprovider import provider


@provider.configure(name="VirshProvider")
class VirshProvider(provider.ProviderFactory):
    """Create VMs from prebuilt templates.

    Sample configuration:

    .. code-block:: json

        {
            "type": "VirshProvider",
            "connection": "alex@performance-01",
            "template_name": "stack-01-devstack-template",
            "template_user": "ubuntu",
            "template_password": "password"
        }

    where :

    * connection - ssh connection to vms host
    * template_name - vm image template
    * template_user - vm user to launch devstack
    * template_password - vm password to launch devstack

    """

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string"
            },
            "connection": {
                "type": "string",
                "pattern": "^.+@.+$"
            },
            "template_name": {
                "type": "string"
            },
            "template_user": {
                "type": "string"
            },
            "template_password": {
                "type": "string"
            }
        },
        "required": ["connection", "template_name", "template_user"]
    }

    def create_servers(self, image_uuid=None, type_id=None, amount=1):
        """Create VMs with chosen image.

        :param image_uuid: Indetificator of image
        :param amount: amount of required VMs
        Returns list of VMs uuids.
        """
        return [self.create_vm(str(uuid.uuid4())) for i in range(amount)]

    def create_vm(self, vm_name):
        """Clone prebuilt VM template and start it."""

        virt_url = self._get_virt_connection_url(self.config["connection"])
        cmd = ["virt-clone", "--connect=%s" % virt_url,
               "-o", self.config["template_name"],
               "-n", vm_name, "--auto-clone"]
        subprocess.check_call(cmd)
        cmd = ["virsh", "--connect=%s" % virt_url, "start", vm_name]
        subprocess.check_call(cmd)
        self.resources.create({"name": vm_name})

        return provider.Server(
            self._determine_vm_ip(vm_name),
            self.config["template_user"],
            password=self.config.get("template_password"),
        )

    def destroy_servers(self):
        """Destroy already created vms."""
        for resource in self.resources.get_all():
            self.destroy_vm(resource["info"]["name"])
            self.resources.delete(resource)

    def destroy_vm(self, vm_name):
        """Destroy single vm and delete all allocated resources."""
        print("Destroy VM %s" % vm_name)
        vconnection = self._get_virt_connection_url(self.config["connection"])

        cmd = ["virsh", "--connect=%s" % vconnection, "destroy", vm_name]
        subprocess.check_call(cmd)

        cmd = ["virsh", "--connect=%s" % vconnection, "undefine", vm_name,
               "--remove-all-storage"]
        subprocess.check_call(cmd)
        return True

    @staticmethod
    def _get_virt_connection_url(connection):
        """Format QEMU connection string from SSH url."""
        return "qemu+ssh://%s/system" % connection

    def _determine_vm_ip(self, vm_name):
        ssh_opt = "-o StrictHostKeyChecking=no"
        script_path = os.path.dirname(__file__) + "/virsh/get_domain_ip.sh"

        cmd = ["scp", ssh_opt, script_path,
               "%s:~/get_domain_ip.sh" % self.config["connection"]]
        subprocess.check_call(cmd)

        tries = 0
        ip = None
        while tries < 3 and not ip:
            cmd = ["ssh", ssh_opt, self.config["connection"],
                   "./get_domain_ip.sh", vm_name]
            out = subprocess.check_output(cmd)
            try:
                ip = netaddr.IPAddress(out)
            except netaddr.core.AddrFormatError:
                ip = None
            tries += 1
            time.sleep(10)
        # TODO(akscram): In case of None this method returns result "None".
        return str(ip)
