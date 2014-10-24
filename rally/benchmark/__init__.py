# Copyright 2014: Mirantis Inc.
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

from rally import utils as rutils


rutils.import_modules_from_package("rally.benchmark.context")
rutils.import_modules_from_package("rally.benchmark.runners")
rutils.import_modules_from_package("rally.benchmark.scenarios")

rutils.load_plugins("/opt/rally/plugins/")
rutils.load_plugins(os.path.expanduser("~/.rally/plugins/"))
