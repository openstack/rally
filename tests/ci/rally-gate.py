#!/usr/bin/env python
#
# Copyright 2015: Mirantis Inc.
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

import errno
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile

from six.moves.urllib import parse

from rally.ui import utils


def use_keystone_v3():
    """Alter deployment to use keystone v3."""
    print("Changing deployment to v3")
    config = json.loads(subprocess.check_output(["rally", "deployment",
                                                 "config"]))
    v3_url = parse.urlsplit(config["auth_url"])._replace(path="v3").geturl()
    config["auth_url"] = v3_url
    endpoint = config.get("endpoint")
    if endpoint:
        v3_enpoint = parse.urlsplit(endpoint)._replace(path="v3").geturl()
        config["endpoint"] = v3_enpoint
    config["project_name"] = config["tenant"]
    config["project_domain_name"] = config["tenant"]
    cfg_file = tempfile.NamedTemporaryFile()
    json.dump(config, cfg_file)
    print("New config for keystone v3:")
    print(json.dumps(config, indent=2))
    cfg_file.flush()
    subprocess.call(["rally", "deployment", "create",
                     "--name", "V3", "--file", cfg_file.name])
    print(subprocess.check_output(["rally", "deployment", "check"]))

TAG_HANDLERS = {"v3": use_keystone_v3}


def perror(s):
    sys.stderr.write(s + "\n")
    sys.stderr.flush()


def run(cmd, stdout=None, gzip=True, check=False):
    """Run shell command.

    Save output to file, and gzip-compress if needed.
    If exit status is non-zero and check is True then raise exception.
    Return exit status otherwise.
    """
    print("Starting %s" % " ".join(cmd))
    status = subprocess.call(cmd, stdout=open(stdout, "w") if stdout else None)
    if stdout and gzip:
        subprocess.call(["gzip", "-9", stdout])
    if check and status:
        raise Exception("Failed with status %d" % status)
    return status


def run_task(task, tags=None):
    new_home_dir = tempfile.mkdtemp(prefix="rally_gate_")
    shutil.copytree(os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".rally"),
                    os.path.join(new_home_dir, ".rally"))
    print("Setting $HOME to %s" % new_home_dir)
    os.environ["HOME"] = new_home_dir
    for tag in tags or []:
        if tag == "args":
            continue
        if tag not in TAG_HANDLERS:
            perror("Warning! Unknown tag '%s'" % tag)
            continue
        try:
            TAG_HANDLERS[tag]()
        except Exception as e:
            perror("Error processing tag '%s': %s" % (tag, e))

    run(["rally", "task", "validate", "--task", task], check=True)
    cmd = ["rally", "task", "start", "--task", task]
    args_file, ext = task.rsplit(".", 1)
    args_file = args_file + "_args." + ext
    if os.path.isfile(args_file):
        cmd += ["--task-args-file", args_file]
    run(cmd, check=True)
    task_name = os.path.split(task)[-1]
    pub_dir = os.environ.get("RCI_PUB_DIR", "rally-plot")
    try:
        os.makedirs(os.path.join(pub_dir, "extra"))
    except Exception as e:
        if e.errno != errno.EEXIST:
            raise
    run(["rally", "task", "report", "--out",
         "%s/%s.html" % (pub_dir, task_name)])
    run(["rally", "task", "results"],
        stdout="%s/results-%s.json" % (pub_dir, task_name))
    status = run(["rally", "task", "sla_check"],
                 stdout="%s/%s.sla.txt" % (pub_dir, task_name))
    run(["rally", "task", "detailed"],
        stdout="rally-plot/detailed-%s.txt" % task_name)
    run(["rally", "task", "detailed", "--iterations-data"],
        stdout="rally-plot/detailed_with_iterations-%s.txt" % task_name)

    return status


def get_name_from_git():
    """Determine org/project name from git."""
    r = re.compile(".*/(.*?)/(.*?).git$")
    for l in open(".git/config"):
        m = r.match(l.strip())
        if m:
            return m.groups()
    raise Exception("Unable to get project name from git")


def get_project_name():
    for var in ("ZUUL_PROJECT", "GERRIT_PROJECT"):
        if var in os.environ:
            return os.environ[var].split("/")
    return get_name_from_git()


def main():
    statuses = []
    org, project = get_project_name()

    base = os.environ.get("BASE")
    if base:
        base_jobs_dir = os.path.join(base, "new", project)
    else:
        base_jobs_dir = os.path.realpath(".")

    rally_root = "/home/rally/rally/"
    if not os.path.exists(rally_root):
        rally_root = os.environ["BASE"] + "/new/rally/"

    jobs_dir = os.path.join(base_jobs_dir, "rally-jobs")
    if not os.path.exists(jobs_dir):
        # fallback to legacy path
        jobs_dir = os.path.join(base_jobs_dir, "rally-scenarios")
    if not os.path.exists(jobs_dir):
        raise Exception("Rally jobs directory does not exist.")

    for directory in ("plugins", "extra"):
        dst = os.path.expanduser("~/.rally/%s" % directory)
        try:
            shutil.copytree(os.path.join(jobs_dir, directory), dst)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    scenario = os.environ.get("RALLY_SCENARIO", project).rsplit(".", 1)
    scenario_name = scenario.pop(0)
    scenario_ext = scenario.pop() if scenario else "yaml"
    print("Processing scenario %s" % scenario_name)

    for fname in os.listdir(jobs_dir):
        print("Processing %s" % fname)
        if fname.startswith(scenario_name):
            tags = fname[len(scenario_name):-len(scenario_ext) - 1].split("_")
            statuses.append(run_task(os.path.join(jobs_dir, fname), tags))
        else:
            print("Ignoring file %s" % fname)
    print("Exit statuses: %r" % statuses)
    template = utils.get_template("ci/index.mako")
    with open("rally-plot/extra/index.html", "w") as output:
        output.write(template.render())
    return any(statuses)


if __name__ == "__main__":
    sys.exit(main())
