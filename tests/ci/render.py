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

from __future__ import print_function
import re
import sys

from rally.ui import utils


HELP_MESSAGE = (
    "Usage:\n\t"
    "render.py ci/template.mako"
    "[<key-1>=<value-1> <key-2>=<value-2> ...]\n\n\t"
    "Where key-1,value-1 and key-2,value-2 are key pairs of template.")


if __name__ == "__main__":
    args = sys.argv
    if (len(args) < 1 or not all(re.match("^[^=]+=[^=]+$",
                                 arg) for arg in args[2:])):
        print(HELP_MESSAGE, file=sys.stderr)
        sys.exit(1)
    render_kwargs = dict([arg.split("=") for arg in args[2:]])
    print(utils.get_template(args[1]).render(**render_kwargs))
