# Copyright 2014: Rackspace UK
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
import pkgutil

from rally.common import logging
from rally.common import sshutils
from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
from rally.plugins.openstack.services import heat
from rally.task import atomic
from rally.task import types
from rally.task import validation


"""Scenarios that are to be run inside VM instances."""


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image", fail_on_404_image=False)
@validation.valid_command("command")
@validation.number("port", minval=1, maxval=65535, nullable=True,
                   integer_only=True)
@validation.external_network_exists("floating_network")
@validation.required_param_or_context(arg_name="image",
                                      ctx_name="image_command_customizer")
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"],
                             "keypair": {}, "allow_ssh": None},
                    name="VMTasks.boot_runcommand_delete")
class BootRuncommandDelete(vm_utils.VMScenario):

    def run(self, flavor, username, password=None,
            image=None,
            command=None,
            volume_args=None, floating_network=None, port=22,
            use_floating_ip=True, force_delete=False, wait_for_ping=True,
            max_log_length=None, **kwargs):
        """Boot a server, run script specified in command and delete server.

        :param image: glance image name to use for the vm. Optional
            in case of specified "image_command_customizer" context
        :param flavor: VM flavor name
        :param username: ssh username on server, str
        :param password: Password on SSH authentication
        :param command: Command-specifying dictionary that either specifies
            remote command path via `remote_path' (can be uploaded from a
            local file specified by `local_path`), an inline script via
            `script_inline' or a local script file path using `script_file'.
            Both `script_file' and `local_path' are checked to be accessible
            by the `file_exists' validator code.

            The `script_inline' and `script_file' both require an `interpreter'
            value to specify the interpreter script should be run with.

            Note that any of `interpreter' and `remote_path' can be an array
            prefixed with environment variables and suffixed with args for
            the `interpreter' command. `remote_path's last component must be
            a path to a command to execute (also upload destination if a
            `local_path' is given). Uploading an interpreter is possible
            but requires that `remote_path' and `interpreter' path do match.

            Examples:

              .. code-block:: python

                # Run a `local_script.pl' file sending it to a remote
                # Perl interpreter
                command = {
                    "script_file": "local_script.pl",
                    "interpreter": "/usr/bin/perl"
                }

                # Run an inline script sending it to a remote interpreter
                command = {
                    "script_inline": "echo 'Hello, World!'",
                    "interpreter": "/bin/sh"
                }

                # Run a remote command
                command = {
                    "remote_path": "/bin/false"
                }

                # Copy a local command and run it
                command = {
                    "remote_path": "/usr/local/bin/fio",
                    "local_path": "/home/foobar/myfiodir/bin/fio"
                }

                # Copy a local command and run it with environment variable
                command = {
                    "remote_path": ["HOME=/root", "/usr/local/bin/fio"],
                    "local_path": "/home/foobar/myfiodir/bin/fio"
                }

                # Run an inline script sending it to a remote interpreter
                command = {
                    "script_inline": "echo \"Hello, ${NAME:-World}\"",
                    "interpreter": ["NAME=Earth", "/bin/sh"]
                }

                # Run an inline script sending it to an uploaded remote
                # interpreter
                command = {
                    "script_inline": "echo \"Hello, ${NAME:-World}\"",
                    "interpreter": ["NAME=Earth", "/tmp/sh"],
                    "remote_path": "/tmp/sh",
                    "local_path": "/home/user/work/cve/sh-1.0/bin/sh"
                }


        :param volume_args: volume args for booting server from volume
        :param floating_network: external network name, for floating ip
        :param port: ssh port for SSH connection
        :param use_floating_ip: bool, floating or fixed IP for SSH connection
        :param force_delete: whether to use force_delete for servers
        :param wait_for_ping: whether to check connectivity on server creation
        :param **kwargs: extra arguments for booting the server
        :param max_log_length: The number of tail nova console-log lines user
                               would like to retrieve
        :returns: dictionary with keys `data' and `errors':
                  data: dict, JSON output from the script
                  errors: str, raw data from the script's stderr stream
        """
        if volume_args:
            volume = self._create_volume(volume_args["size"], imageRef=None)
            kwargs["block_device_mapping"] = {"vdrally": "%s:::1" % volume.id}

        if not image:
            image = self.context["tenant"]["custom_image"]["id"]

        server, fip = self._boot_server_with_fip(
            image, flavor, use_floating_ip=use_floating_ip,
            floating_network=floating_network,
            key_name=self.context["user"]["keypair"]["name"],
            **kwargs)
        try:
            if wait_for_ping:
                self._wait_for_ping(fip["ip"])

            code, out, err = self._run_command(
                fip["ip"], port, username, password, command=command)
            text_area_output = ["StdErr: %s" % (err or "(none)"),
                                "StdOut:"]
            if code:
                raise exceptions.ScriptError(
                    "Error running command %(command)s. "
                    "Error %(code)s: %(error)s" % {
                        "command": command, "code": code, "error": err})
            # Let's try to load output data
            try:
                data = json.loads(out)
                # 'echo 42' produces very json-compatible result
                #  - check it here
                if not isinstance(data, dict):
                    raise ValueError
            except ValueError:
                # It's not a JSON, probably it's 'script_inline' result
                data = []
        except (exceptions.TimeoutException,
                exceptions.SSHTimeout):
            console_logs = self._get_server_console_output(server,
                                                           max_log_length)
            LOG.debug("VM console logs:\n%s", console_logs)
            raise

        finally:
            self._delete_server_with_fip(server, fip,
                                         force_delete=force_delete)

        if isinstance(data, dict) and set(data) == {"additive", "complete"}:
            for chart_type, charts in data.items():
                for chart in charts:
                    self.add_output(**{chart_type: chart})
        else:
            # it's a dict with several unknown lines
            text_area_output.extend(out.split("\n"))
            self.add_output(complete={"title": "Script Output",
                                      "chart_plugin": "TextArea",
                                      "data": text_area_output})


@scenario.configure(context={"cleanup": ["nova", "heat"],
                             "keypair": {}, "network": {}},
                    name="VMTasks.runcommand_heat")
class RuncommandHeat(vm_utils.VMScenario):

    def run(self, workload, template, files, parameters):
        """Run workload on stack deployed by heat.

         Workload can be either file or resource:

           .. code-block:: json

             {"file": "/path/to/file.sh"}
             {"resource": ["package.module", "workload.py"]}


         Also it should contain "username" key.

         Given file will be uploaded to `gate_node` and started. This script
         should print `key` `value` pairs separated by colon. These pairs will
         be presented in results.

         Gate node should be accessible via ssh with keypair `key_name`, so
         heat template should accept parameter `key_name`.

        :param workload: workload to run
        :param template: path to heat template file
        :param files: additional template files
        :param parameters: parameters for heat template
        """
        keypair = self.context["user"]["keypair"]
        parameters["key_name"] = keypair["name"]
        network = self.context["tenant"]["networks"][0]
        parameters["router_id"] = network["router_id"]
        self.stack = heat.main.Stack(self, self.task,
                                     template, files=files,
                                     parameters=parameters)
        self.stack.create()
        for output in self.stack.stack.outputs:
            if output["output_key"] == "gate_node":
                ip = output["output_value"]
                break
        ssh = sshutils.SSH(workload["username"], ip, pkey=keypair["private"])
        ssh.wait()
        script = workload.get("resource")
        if script:
            script = pkgutil.get_data(*script)
        else:
            script = open(workload["file"]).read()
        ssh.execute("cat > /tmp/.rally-workload", stdin=script)
        ssh.execute("chmod +x /tmp/.rally-workload")
        with atomic.ActionTimer(self, "runcommand_heat.workload"):
            status, out, err = ssh.execute(
                "/tmp/.rally-workload",
                stdin=json.dumps(self.stack.stack.outputs))
        rows = []
        for line in out.splitlines():
            row = line.split(":")
            if len(row) != 2:
                raise exceptions.ScriptError("Invalid data '%s'" % line)
            rows.append(row)
        if not rows:
            raise exceptions.ScriptError("No data returned. Original error "
                                         "message is %s" % err)
        self.add_output(
            complete={"title": "Workload summary",
                      "description": "Data generated by workload",
                      "chart_plugin": "Table",
                      "data": {
                          "cols": ["key", "value"],
                          "rows": rows}}
        )

BASH_DD_LOAD_TEST = """
#!/bin/sh
# Load server and output JSON results ready to be processed
# by Rally scenario

for ex in awk top grep free tr df dc dd gzip
do
    if ! type ${ex} >/dev/null
    then
        echo "Executable is required by script but not available\
         on a server: ${ex}" >&2
        return 1
    fi
done

get_used_cpu_percent() {
    echo 100\
     $(top -b -n 1 | grep -i CPU | head -n 1 | awk '{print $8}' | tr -d %)\
      - p | dc
}

get_used_ram_percent() {
    local total=$(free | grep Mem: | awk '{print $2}')
    local used=$(free | grep -- -/+\ buffers | awk '{print $3}')
    echo ${used} 100 \* ${total} / p | dc
}

get_used_disk_percent() {
    df -P / | grep -v Filesystem | awk '{print $5}' | tr -d %
}

get_seconds() {
    (time -p ${1}) 2>&1 | awk '/real/{print $2}'
}

complete_load() {
    local script_file=${LOAD_SCRIPT_FILE:-/tmp/load.sh}
    local stop_file=${LOAD_STOP_FILE:-/tmp/load.stop}
    local processes_num=${LOAD_PROCESSES_COUNT:-20}
    local size=${LOAD_SIZE_MB:-5}

    cat << EOF > ${script_file}
until test -e ${stop_file}
do dd if=/dev/urandom bs=1M count=${size} 2>/dev/null | gzip >/dev/null ; done
EOF

    local sep
    local cpu
    local ram
    local dis
    rm -f ${stop_file}
    for i in $(seq ${processes_num})
    do
        i=$((i-1))
        sh ${script_file} &
        cpu="${cpu}${sep}[${i}, $(get_used_cpu_percent)]"
        ram="${ram}${sep}[${i}, $(get_used_ram_percent)]"
        dis="${dis}${sep}[${i}, $(get_used_disk_percent)]"
        sep=", "
    done
    > ${stop_file}
    cat << EOF
    {
      "title": "Generate load by spawning processes",
      "description": "Each process runs gzip for ${size}M urandom data\
       in a loop",
      "chart_plugin": "Lines",
      "axis_label": "Number of processes",
      "label": "Usage, %",
      "data": [
        ["CPU", [${cpu}]],
        ["Memory", [${ram}]],
        ["Disk", [${dis}]]]
    }
EOF
}

additive_dd() {
    local c=${1:-50} # Megabytes
    local file=/tmp/dd_test.img
    local write=$(get_seconds "dd if=/dev/urandom of=${file} bs=1M count=${c}")
    local read=$(get_seconds "dd if=${file} of=/dev/null bs=1M count=${c}")
    local gzip=$(get_seconds "gzip ${file}")
    rm ${file}.gz
    cat << EOF
    {
      "title": "Write, read and gzip file",
      "description": "Using file '${file}', size ${c}Mb.",
      "chart_plugin": "StackedArea",
      "data": [
        ["write_${c}M", ${write}],
        ["read_${c}M", ${read}],
        ["gzip_${c}M", ${gzip}]]
    },
    {
      "title": "Statistics for write/read/gzip",
      "chart_plugin": "StatsTable",
      "data": [
        ["write_${c}M", ${write}],
        ["read_${c}M", ${read}],
        ["gzip_${c}M", ${gzip}]]
    }

EOF
}

cat << EOF
{
  "additive": [$(additive_dd)],
  "complete": [$(complete_load)]
}
EOF
"""


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.image_valid_on_flavor("flavor", "image")
@validation.valid_command("command")
@validation.number("port", minval=1, maxval=65535, nullable=True,
                   integer_only=True)
@validation.external_network_exists("floating_network")
@validation.required_services(consts.Service.NOVA, consts.Service.CINDER)
@validation.required_openstack(users=True)
@scenario.configure(context={"cleanup": ["nova", "cinder"],
                             "keypair": {}, "allow_ssh": None},
                    name="VMTasks.dd_load_test")
class DDLoadTest(BootRuncommandDelete):

    def run(self, command, **kwargs):
        """Boot a server from a custom image, run a command that outputs JSON.

        Example Script in rally-jobs/extra/install_benchmark.sh
        :param command: default parameter from scenario
        """
        command["script_inline"] = BASH_DD_LOAD_TEST
        return super(DDLoadTest, self).run(command=command, **kwargs)
