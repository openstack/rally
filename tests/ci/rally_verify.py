#!/usr/bin/env python
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

import argparse
import gzip
import json
import logging
import os
import re
import subprocess
import sys
import uuid

from rally.cli import envutils
from rally.common import objects
from rally import osclients
from rally.ui import utils

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

BASE_DIR = "rally-verify"

MODES = {"full": "--pattern set=full", "light": "--pattern set=smoke"}
DEPLOYMENT_NAME = "devstack"
VERIFIER_TYPE = "tempest"
VERIFIER_SOURCE = "https://git.openstack.org/openstack/tempest"
VERIFIER_EXT_REPO = "https://git.openstack.org/openstack/keystone"
VERIFIER_EXT_NAME = "keystone_tests"
SKIP_TESTS = (
    "tempest.api.compute.flavors.test_flavors.FlavorsV2TestJSON."
    "test_get_flavor[id-1f12046b-753d-40d2-abb6-d8eb8b30cb2f,smoke]: "
    "This test was skipped intentionally")
XFAIL_TESTS = (
    "tempest.api.compute.servers.test_server_actions.ServerActionsTestJSON."
    "test_get_vnc_console[id-c6bc11bf-592e-4015-9319-1c98dc64daf5]: "
    "This test fails because 'novnc' console type is unavailable")
TEST_NAME_RE = re.compile(r"^[a-zA-Z_.0-9]+(\[[a-zA-Z-,=0-9]*\])?$")

# NOTE(andreykurilin): this variable is used to generate output file names
# with prefix ${CALL_COUNT}_ .
_call_count = 0
# NOTE(andreykurilin): if some command fails, script should end with
# error status
_return_status = 0


def call_rally(cmd, print_output=False, output_type=None):
    """Execute a Rally command and write result in files."""
    global _return_status
    global _call_count
    _call_count += 1

    data = {"cmd": "rally --rally-debug %s" % cmd}
    stdout_file = "{base_dir}/{prefix}_{cmd}.txt.gz"

    cmd = cmd.replace("/", "_")
    data.update({"stdout_file": stdout_file.format(base_dir=BASE_DIR,
                                                   prefix=_call_count,
                                                   cmd=cmd.replace(" ", "_"))})

    if output_type:
        data["output_file"] = data["stdout_file"].replace(
            ".txt.", ".%s." % output_type)
        data["cmd"] += " --file %s" % data["output_file"]
        if output_type == "html":
            data["cmd"] += " --html"

    try:
        LOG.info("Try to execute `%s`." % data["cmd"])
        stdout = subprocess.check_output(data["cmd"].split(),
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.error("Command `%s` failed." % data["cmd"])
        stdout = e.output
        data["status"] = "fail"
        _return_status = 1
    else:
        data["status"] = "success"

    if output_type:
        # let's gzip results
        with open(data["output_file"]) as f:
            output = f.read()
        with gzip.open(data["output_file"], "wb") as f:
            f.write(output)

    stdout = "$ %s\n%s" % (data["cmd"], stdout)

    with gzip.open(data["stdout_file"], "wb") as f:
        f.write(stdout)

    if print_output:
        print(stdout)

    return data


def start_verification(args):
    """Start a verification, show results and generate reports."""
    results = call_rally("verify start %s" % args)
    results["uuid"] = envutils.get_global(envutils.ENV_VERIFICATION)
    results["show"] = call_rally("verify show")
    results["show_detailed"] = call_rally("verify show --detailed")
    for ot in ("json", "html"):
        results[ot] = call_rally("verify report", output_type=ot)
    # NOTE(andreykurilin): we need to clean verification uuid from global
    # environment to be able to load it next time(for another verification).
    envutils.clear_global(envutils.ENV_VERIFICATION)
    return results


def write_file(filename, data):
    """Create a file and write some data to it."""
    path = os.path.join(BASE_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def generate_trends_reports(uuid_1, uuid_2):
    """Generate trends reports."""
    results = {}
    for ot in ("json", "html"):
        results[ot] = call_rally(
            "verify report --uuid %s %s" % (uuid_1, uuid_2), output_type=ot)
    return results


def render_page(**render_vars):
    template = utils.get_template("ci/index_verify.html")
    with open(os.path.join(BASE_DIR, "extra/index.html"), "w") as f:
        f.write(template.render(**render_vars))


def main():
    parser = argparse.ArgumentParser(description="Launch rally-verify job.")
    parser.add_argument("--mode", type=str, default="light",
                        help="Mode of job. The 'full' mode corresponds to the "
                             "full set of verifier tests. The 'light' mode "
                             "corresponds to the smoke set of verifier tests.",
                        choices=MODES.keys())
    parser.add_argument("--compare", action="store_true",
                        help="Start the second verification to generate a "
                             "trends report for two verifications.")
    # TODO(ylobankov): Remove hard-coded Tempest related things and make it
    #                  configurable.
    parser.add_argument("--ctx-create-resources", action="store_true",
                        help="Make Tempest context create needed resources "
                             "for the tests.")

    args = parser.parse_args()

    if not os.path.exists("%s/extra" % BASE_DIR):
        os.makedirs("%s/extra" % BASE_DIR)

    # Choose and check the deployment
    call_rally("deployment use --deployment %s" % DEPLOYMENT_NAME)
    call_rally("deployment check")

    config = json.loads(
        subprocess.check_output(["rally", "deployment", "config"]))
    config.update(config.pop("admin"))
    del config["type"]
    clients = osclients.Clients(objects.Credential(**config))

    if args.ctx_create_resources:
        # If the 'ctx-create-resources' arg is provided, delete images and
        # flavors, and also create a shared network to make Tempest context
        # create needed resources.
        LOG.info("The 'ctx-create-resources' arg is provided. Deleting "
                 "images and flavors, and also creating a shared network "
                 "to make Tempest context create needed resources.")

        LOG.info("Deleting images.")
        for image in clients.glance().images.list():
            clients.glance().images.delete(image.id)

        LOG.info("Deleting flavors.")
        for flavor in clients.nova().flavors.list():
            clients.nova().flavors.delete(flavor.id)

        LOG.info("Creating a shared network.")
        net_body = {
            "network": {
                "name": "shared-net-%s" % str(uuid.uuid4()),
                "tenant_id": clients.keystone.auth_ref.project_id,
                "shared": True
            }
        }
        clients.neutron().create_network(net_body)
    else:
        # Otherwise, just in case create only flavors with the following
        # properties: RAM = 64MB and 128MB, VCPUs = 1, disk = 0GB to make
        # Tempest context discover them.
        LOG.info("The 'ctx-create-resources' arg is not provided. "
                 "Creating flavors to make Tempest context discover them.")
        for flv_ram in [64, 128]:
            params = {
                "name": "flavor-%s" % str(uuid.uuid4()),
                "ram": flv_ram,
                "vcpus": 1,
                "disk": 0
            }
            LOG.info(
                "Creating flavor '%s' with the following properties: RAM "
                "= %dMB, VCPUs = 1, disk = 0GB" % (params["name"], flv_ram))
            clients.nova().flavors.create(**params)

    render_vars = dict(verifications=[])

    # List plugins for verifiers management
    render_vars["list_plugins"] = call_rally("verify list-plugins")

    # Create a verifier
    render_vars["create_verifier"] = call_rally(
        "verify create-verifier --type %s --name my-verifier --source %s"
        % (VERIFIER_TYPE, VERIFIER_SOURCE))

    # List verifiers
    render_vars["list_verifiers"] = call_rally("verify list-verifiers")

    # Get verifier ID
    verifier_id = envutils.get_global(envutils.ENV_VERIFIER)
    # Get the penultimate verifier commit ID
    repo_dir = os.path.join(
        os.path.expanduser("~"),
        ".rally/verification/verifier-%s/repo" % verifier_id)
    p_commit_id = subprocess.check_output(
        ["git", "log", "-n", "1", "--pretty=format:%H"], cwd=repo_dir).strip()
    # Switch the verifier to the penultimate version
    render_vars["update_verifier"] = call_rally(
        "verify update-verifier --version %s --update-venv" % p_commit_id)

    # Generate and show the verifier config file
    render_vars["configure_verifier"] = call_rally(
        "verify configure-verifier --show")

    # Add a verifier extension
    render_vars["add_verifier_ext"] = call_rally(
        "verify add-verifier-ext --source %s" % VERIFIER_EXT_REPO)

    # List verifier extensions
    render_vars["list_verifier_exts"] = call_rally("verify list-verifier-exts")

    # List verifier tests
    render_vars["list_verifier_tests"] = call_rally(
        "verify list-verifier-tests %s" % MODES[args.mode])

    # Start a verification, show results and generate reports
    skip_list_path = write_file("skip-list.yaml", SKIP_TESTS)
    xfail_list_path = write_file("xfail-list.yaml", XFAIL_TESTS)
    run_args = ("%s --skip-list %s --xfail-list %s"
                % (MODES[args.mode], skip_list_path, xfail_list_path))
    render_vars["verifications"].append(start_verification(run_args))

    if args.compare:
        # Start another verification, show results and generate reports
        with gzip.open(render_vars["list_verifier_tests"]["stdout_file"]) as f:
            tests = [t for t in f.read().split("\n") if TEST_NAME_RE.match(t)]
            load_list_path = write_file("load-list.txt", "\n".join(tests))
        run_args = "--load-list %s" % load_list_path
        render_vars["verifications"].append(start_verification(run_args))

        # Generate trends reports for two verifications
        render_vars["compare"] = generate_trends_reports(
            render_vars["verifications"][-2]["uuid"],
            render_vars["verifications"][-1]["uuid"])

    # List verifications
    render_vars["list"] = call_rally("verify list")

    # Delete the verifier extension
    render_vars["delete_verifier_ext"] = call_rally(
        "verify delete-verifier-ext --name %s" % VERIFIER_EXT_NAME)
    # Delete the verifier and all verifications
    render_vars["delete_verifier"] = call_rally(
        "verify delete-verifier --force")

    render_page(**render_vars)

    return _return_status

if __name__ == "__main__":
    sys.exit(main())
