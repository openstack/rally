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
import subprocess
import sys
import uuid


def create_cfg_for_using_sqlite():
    """Create a config file for rally with path to temporary sqlite database"""
    run_id = str(uuid.uuid4())[:8]

    cfg_path = f"/tmp/self_rally_{run_id}.conf"

    cfg = (f"[database]\n"
           f"connection = sqlite:////tmp/self-rally-{run_id}.sqlite")
    with open(cfg_path, "w") as f:
        f.write(cfg)

    return "--config-file", cfg_path


def _print_with_wrapper(*messages):
    print("#" * 80)
    for m in messages:
        print(f"# {m}")
    print("#" * 80)


class Rally(object):
    def __init__(self, rally_cmd):
        self._rally_cmd = rally_cmd

    def __call__(self, cmd, debug=False, description=None):
        if not isinstance(cmd, (tuple, list)):
            cmd = cmd.split(" ")

        final_cmd = self._rally_cmd[:]
        if debug:
            final_cmd.append("--debug")
        final_cmd.extend(cmd)

        messages = [f"Calling: {' '.join(final_cmd)}"]
        if description:
            messages.append(f"Description: {description}")
        _print_with_wrapper(*messages)

        p = subprocess.Popen(
            final_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        for line in iter(p.stdout.readline, b""):
            print(line.rstrip().decode("utf-8"))
        p.wait()
        if p.returncode != 0:
            _print_with_wrapper(
                f"Command returned non-zero exit status {p.returncode}.")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        "rally_self_job",
        description="A script that ensures that Rally works after installation"
    )
    parser.add_argument(
        "--results-dir", type=str, default=".test_results",
        help="A path to directory to place rally results execution."
    )
    parser.add_argument(
        "--task", type=str, required=True,
        help="A simple task to launch."
    )
    parser.add_argument(
        "--without-tmp-sqlite", action="store_false",
        dest="prepare_sqlite",
        help="Do not create a tmp sqlite db for Rally"
    )
    parser.add_argument(
        "--rally-cmd", type=str, default="rally",
        help="An override 'rally' entry point for all commands."
    )
    parser.add_argument(
        "--plugins-path", type=str, required=True,
        help="A path to external rally plugins that include "
             "'FakePlugin.testplugin'"
    )

    args = parser.parse_args()

    rally_cmd = args.rally_cmd.split(" ")
    if "--config-file" in rally_cmd:
        raise Exception(
            "It is restricted to use '--config-file' at rally cmd.")

    if args.prepare_sqlite:
        rally_cmd.extend(create_cfg_for_using_sqlite())

    rally_cmd.append(f"--plugin-paths={args.plugins_path}")

    rally = Rally(rally_cmd)

    rally("--version")
    rally("plugin show --name FakePlugin.testplugin", debug=True,
          description="Ensure plugins loading")

    rally("db create", description="Initialize temporary sqlite database")

    rally("env create --name=self",
          description="Create empty environment")
    rally(f"task start {args.task}")

    results_dir = args.results_dir
    rally(f"task report --html-static --out {results_dir}/self_report.html")
    rally(f"task report --json --out {results_dir}/self_report.json")
    rally("task sla-check")


if __name__ == "__main__":
    main()
