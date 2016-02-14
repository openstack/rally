#!/usr/bin/env python
#
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

"""Run HTTP benchmark by runcommand_heat scenario."""

import json
import re
import subprocess
import sys
import tempfile


SIEGE_RE = re.compile(r"^(Throughput|Transaction rate):\s+(\d+\.\d+)\s+.*")


def get_instances():
    outputs = json.load(sys.stdin)
    for output in outputs:
        if output["output_key"] == "wp_nodes":
            for node in output["output_value"].values():
                yield node["wordpress-network"][0]


def generate_urls_list(instances):
    urls = tempfile.NamedTemporaryFile(delete=False)
    with urls:
        for inst in instances:
            for i in range(1, 1000):
                urls.write("http://%s/wordpress/index.php/%d/\n" % (inst, i))
    return urls.name


def run():
    instances = list(get_instances())
    urls = generate_urls_list(instances)
    out = subprocess.check_output("siege -q -t 60S -b -f %s" % urls,
                                  shell=True, stderr=subprocess.STDOUT)
    for line in out.splitlines():
        m = SIEGE_RE.match(line)
        if m:
            sys.stdout.write("%s:%s\n" % m.groups())


if __name__ == "__main__":
    sys.exit(run())
