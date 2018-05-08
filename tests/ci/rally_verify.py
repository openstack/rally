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
import collections
import gzip
import json
import logging
import os
import re
import subprocess
import sys
import uuid

from rally_openstack import osclients

from rally import api
from rally.ui import utils

LOG = logging.getLogger("verify-job")
LOG.setLevel(logging.DEBUG)

# NOTE(andreykurilin): this variable is used to generate output file names
# with prefix ${CALL_COUNT}_ .
_call_count = 0


class Status(object):
    PASS = "success"
    ERROR = "error"
    SKIPPED = "skip"
    FAILURE = "fail"


class Step(object):
    COMMAND = None
    DEPENDS_ON = None
    CALL_ARGS = {}

    BASE_DIR = "rally-verify"
    HTML_TEMPLATE = ("<span class=\"%(status)s\">[%(status)s]</span>\n"
                     "<a href=\"%(output_file)s\">%(doc)s</a>\n"
                     "<code>$ %(cmd)s</code>")

    def __init__(self, args, rapi):
        self.args = args
        self.rapi = rapi
        self.result = {"status": Status.PASS,
                       "doc": self.__doc__}

    @property
    def name(self):
        return " ".join(re.findall("[A-Z][^A-Z]*",
                                   self.__class__.__name__)).lower()

    def check(self, results):
        """Check weather this step should be executed or skipped."""
        if self.DEPENDS_ON is not None:
            if results[self.DEPENDS_ON].result["status"] in (
                    Status.PASS, Status.FAILURE):
                return True
            else:
                self.result["status"] = Status.SKIPPED
                msg = ("Step '%s' is skipped, since depends on step '%s' is "
                       "skipped or finished with an error." %
                       (self.name, results[self.DEPENDS_ON].name))
                stdout_file = self._generate_path(
                    "%s.txt.gz" % self.__class__.__name__)

                self.result["output_file"] = self._write_file(
                    stdout_file, msg, compress=True)
                return False
        return True

    def setUp(self):
        """Obtain variables required for execution"""
        pass

    def run(self):
        """Execute step. The default action - execute the command"""
        self.setUp()

        cmd = "rally --rally-debug %s" % (self.COMMAND % self.CALL_ARGS)
        self.result["cmd"] = cmd
        self.result["status"], self.result["output"] = self.call_rally(cmd)

        stdout_file = self._generate_path("%s.txt.gz" % cmd)
        self.result["output_file"] = self._write_file(
            stdout_file, self.result["output"], compress=True)

    @classmethod
    def _generate_path(cls, root):
        global _call_count
        _call_count += 1

        root = root.replace("<", "").replace(">", "").replace("/", "_")
        parts = ["%s" % _call_count]
        for path in root.split(" "):
            if path.startswith(cls.BASE_DIR):
                path = path[len(cls.BASE_DIR) + 1:]
            parts.append(path)
        return os.path.join(cls.BASE_DIR, "_".join(parts))

    @classmethod
    def _write_file(cls, path, data, compress=False):
        """Create a file and write some data to it."""
        if compress:
            with gzip.open(path, "wb") as f:
                f.write(data)
        else:
            with open(path, "wb") as f:
                f.write(data)
        return path

    @staticmethod
    def call_rally(command):
        """Execute a Rally verify command."""
        try:
            LOG.info("Start `%s` command." % command)
            stdout = subprocess.check_output(command.split(),
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.error("Command `%s` failed." % command)
            return Status.ERROR, e.output
        else:
            return Status.PASS, stdout

    def to_html(self):
        return self.HTML_TEMPLATE % self.result


class SetUpStep(Step):
    """Validate deployment, create required resources and directories."""

    DEPLOYMENT_NAME = "devstack"

    def run(self):
        if not os.path.exists("%s/extra" % self.BASE_DIR):
            os.makedirs("%s/extra" % self.BASE_DIR)

        # ensure that deployment exit
        deployment = self.rapi.deployment._get(self.DEPLOYMENT_NAME)
        # check it
        result = self.rapi.deployment.check(
            deployment=self.DEPLOYMENT_NAME)["openstack"]
        if "admin_error" in result[0] or "user_error" in result[0]:
            self.result["status"] = Status.ERROR
            return

        try:
            subprocess.check_call(["rally", "deployment", "use",
                                   "--deployment", self.DEPLOYMENT_NAME],
                                  stdout=sys.stdout)
        except subprocess.CalledProcessError:
            self.result["status"] = Status.ERROR
            return

        credentials = None
        for platform, creds in deployment.to_dict()["credentials"].items():
            if platform == "openstack":
                credentials = creds[0]["admin"]
        if credentials is None:
            return Status.ERROR, "There is no openstack credentials."

        clients = osclients.Clients(credentials)

        if self.args.ctx_create_resources:
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
                LOG.info("Creating flavor '%s' with the following properties: "
                         "RAM = %dMB, VCPUs = 1, disk = 0GB" %
                         (params["name"], flv_ram))
                clients.nova().flavors.create(**params)

    def to_html(self):
        return ""


class ListPlugins(Step):
    """List plugins for verifiers management."""

    COMMAND = "verify list-plugins"
    DEPENDS_ON = SetUpStep


class CreateVerifier(Step):
    """Create a Tempest verifier."""

    COMMAND = ("verify create-verifier --type %(type)s --name %(name)s "
               "--source %(source)s")
    DEPENDS_ON = ListPlugins
    CALL_ARGS = {"type": "tempest",
                 "name": "my-verifier",
                 "source": "https://git.openstack.org/openstack/tempest"}


class ShowVerifier(Step):
    """Show information about the created verifier."""

    COMMAND = "verify show-verifier"
    DEPENDS_ON = CreateVerifier


class ListVerifiers(Step):
    """List all installed verifiers."""

    COMMAND = "verify list-verifiers"
    DEPENDS_ON = CreateVerifier


class UpdateVerifier(Step):
    """Switch the verifier to the penultimate version."""

    COMMAND = "verify update-verifier --version %(version)s --update-venv"
    DEPENDS_ON = CreateVerifier

    def setUp(self):
        """Obtain penultimate verifier commit for downgrading to it"""
        verifier_id = self.rapi.verifier.list()[0]["uuid"]
        verifications_dir = os.path.join(
            os.path.expanduser("~"),
            ".rally/verification/verifier-%s/repo" % verifier_id)
        # Get the penultimate verifier commit ID
        p_commit_id = subprocess.check_output(
            ["git", "log", "-n", "1", "--pretty=format:%H"],
            cwd=verifications_dir).strip()
        self.CALL_ARGS = {"version": p_commit_id}


class ConfigureVerifier(Step):
    """Generate and show the verifier config file."""

    COMMAND = "verify configure-verifier --show"
    DEPENDS_ON = CreateVerifier


class ExtendVerifier(Step):
    """Extend verifier with keystone integration tests."""

    COMMAND = "verify add-verifier-ext --source %(source)s"
    DEPENDS_ON = CreateVerifier
    CALL_ARGS = {"source": "https://git.openstack.org/openstack/"
                           "keystone-tempest-plugin"}


class ListVerifierExtensions(Step):
    """List all extensions of verifier."""

    COMMAND = "verify list-verifier-exts"
    DEPENDS_ON = ExtendVerifier


class ListVerifierTests(Step):
    """List all tests of specific verifier."""

    COMMAND = "verify list-verifier-tests"
    DEPENDS_ON = CreateVerifier


class RunVerification(Step):
    """Run a verification."""

    DEPENDS_ON = ConfigureVerifier
    COMMAND = ("verify start --pattern set=%(set)s --skip-list %(skip_tests)s "
               "--xfail-list %(xfail_tests)s --tag %(tag)s %(set)s-set "
               "--detailed")
    SKIP_TESTS = {
        "tempest.api.compute.flavors.test_flavors.FlavorsV2TestJSON."
        "test_get_flavor[id-1f12046b-753d-40d2-abb6-d8eb8b30cb2f,smoke]":
            "This test was skipped intentionally"}
    XFAIL_TESTS = {
        "tempest.api.compute.servers.test_server_actions."
        "ServerActionsTestJSON.test_get_vnc_console"
        "[id-c6bc11bf-592e-4015-9319-1c98dc64daf5]":
            "This test fails because 'novnc' console type is unavailable"}

    def setUp(self):
        self.CALL_ARGS["tag"] = "tag-1 tag-2"
        self.CALL_ARGS["set"] = "full" if self.args.mode == "full" else "smoke"
        # Start a verification, show results and generate reports
        skip_tests = json.dumps(self.SKIP_TESTS)
        xfail_tests = json.dumps(self.XFAIL_TESTS)
        self.CALL_ARGS["skip_tests"] = self._write_file(
            self._generate_path("skip-list.json"), skip_tests)
        self.CALL_ARGS["xfail_tests"] = self._write_file(
            self._generate_path("xfail-list.json"), xfail_tests)

    def run(self):
        super(RunVerification, self).run()
        if "Success: 0" in self.result["output"]:
            self.result["status"] = Status.FAILURE


class ReRunVerification(RunVerification):
    """Re-Run previous verification."""

    COMMAND = "verify rerun --tag one-more-attempt"


class ShowVerification(Step):
    """Show results of verification."""

    COMMAND = "verify show"
    DEPENDS_ON = RunVerification


class ShowSecondVerification(ShowVerification):
    """Show results of verification."""

    DEPENDS_ON = ReRunVerification


class ShowDetailedVerification(Step):
    """Show detailed results of verification."""

    COMMAND = "verify show --detailed"
    DEPENDS_ON = RunVerification


class ShowDetailedSecondVerification(ShowDetailedVerification):
    """Show detailed results of verification."""

    DEPENDS_ON = ReRunVerification


class ReportVerificationMixin(Step):
    """Mixin for obtaining reports of verifications."""

    COMMAND = "verify report --uuid %(uuids)s --type %(type)s --to %(out)s"

    HTML_TEMPLATE = ("<span class=\"%(status)s\">[%(status)s]</span>\n"
                     "<a href=\"%(out)s\">%(doc)s</a> "
                     "[<a href=\"%(output_file)s\">Output from CLI</a>]\n"
                     "<code>$ %(cmd)s</code>")

    def setUp(self):
        self.CALL_ARGS["out"] = "<path>"
        self.CALL_ARGS["uuids"] = "<uuid-1> <uuid-2>"
        cmd = self.COMMAND % self.CALL_ARGS
        report = "%s.%s" % (cmd.replace("/", "_").replace(" ", "_"),
                            self.CALL_ARGS["type"])
        print(report)
        self.CALL_ARGS["out"] = self._generate_path(report)
        self.CALL_ARGS["uuids"] = " ".join(
            [v["uuid"] for v in self.rapi.verification.list()])
        print(self.COMMAND % self.CALL_ARGS)

    def run(self):
        super(ReportVerificationMixin, self).run()
        creport = "%s.gz" % self.CALL_ARGS["out"]
        with open(self.CALL_ARGS["out"], "rb") as f_in:
            with gzip.open(creport, "wb") as f_out:
                f_out.writelines(f_in)
        self.result["out"] = creport


class HtmlVerificationReport(ReportVerificationMixin):
    """Generate HTML report for verification(s)."""

    CALL_ARGS = {"type": "html-static"}
    DEPENDS_ON = RunVerification

    def setUp(self):
        super(HtmlVerificationReport, self).setUp()
        self.CALL_ARGS["out"] = self.CALL_ARGS["out"][:-7]


class JsonVerificationReport(ReportVerificationMixin):
    """Generate JSON report for verification(s)."""

    CALL_ARGS = {"type": "json"}
    DEPENDS_ON = RunVerification


class JunitVerificationReport(ReportVerificationMixin):
    """Generate JUNIT report for verification(s)."""

    CALL_ARGS = {"type": "junit-xml"}
    DEPENDS_ON = RunVerification


class ListVerifications(Step):
    """List all verifications."""

    COMMAND = "verify list"
    DEPENDS_ON = CreateVerifier


class DeleteVerifierExtension(Step):
    """Delete keystone extension."""

    COMMAND = "verify delete-verifier-ext --name %(name)s"
    CALL_ARGS = {"name": "keystone_tests"}
    DEPENDS_ON = ExtendVerifier


class DeleteVerifier(Step):
    """Delete only Tempest verifier.

    all verifications will be delete when destroy deployment.

    """
    COMMAND = "verify delete-verifier --id %(id)s --force"
    CALL_ARGS = {"id": CreateVerifier.CALL_ARGS["name"]}
    DEPENDS_ON = CreateVerifier


class DestroyDeployment(Step):
    """Delete the deployment, and verifications of this deployment."""

    COMMAND = "deployment destroy --deployment %(id)s"
    CALL_ARGS = {"id": SetUpStep.DEPLOYMENT_NAME}
    DEPENDS_ON = SetUpStep


def run(args):

    steps = [SetUpStep,
             ListPlugins,
             CreateVerifier,
             ShowVerifier,
             ListVerifiers,
             UpdateVerifier,
             ConfigureVerifier,
             ExtendVerifier,
             ListVerifierExtensions,
             ListVerifierTests,
             RunVerification,
             ShowVerification,
             ShowDetailedVerification,
             HtmlVerificationReport,
             JsonVerificationReport,
             JunitVerificationReport,
             ListVerifications,
             DeleteVerifierExtension,
             DestroyDeployment,
             DeleteVerifier]

    if args.compare:
        # need to launch one more verification
        place_to_insert = steps.index(ShowDetailedVerification) + 1
        # insert steps in reverse order to be able to use the same index
        steps.insert(place_to_insert, ShowDetailedSecondVerification)
        steps.insert(place_to_insert, ShowSecondVerification)
        steps.insert(place_to_insert, ReRunVerification)

    results = collections.OrderedDict()
    rapi = api.API()
    for step_cls in steps:
        step = step_cls(args, rapi=rapi)
        if step.check(results):
            step.run()
        results[step_cls] = step

    return results.values()


def main():
    parser = argparse.ArgumentParser(description="Launch rally-verify job.")
    parser.add_argument("--mode", type=str, default="light",
                        help="Mode of job. The 'full' mode corresponds to the "
                             "full set of verifier tests. The 'light' mode "
                             "corresponds to the smoke set of verifier tests.",
                        choices=["light", "full"])
    parser.add_argument("--compare", action="store_true",
                        help="Start the second verification to generate a "
                             "trends report for two verifications.")
    # TODO(ylobankov): Remove hard-coded Tempest related things and make it
    #                  configurable.
    parser.add_argument("--ctx-create-resources", action="store_true",
                        help="Make Tempest context create needed resources "
                             "for the tests.")
    return

    args = parser.parse_args()

    steps = run(args)
    results = [step.to_html() for step in steps]

    template = utils.get_template("ci/index_verify.html")
    with open(os.path.join(Step.BASE_DIR, "extra/index.html"), "w") as f:
        f.write(template.render(steps=results))

    if len([None for step in steps
            if step.result["status"] == Status.PASS]) == len(steps):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
