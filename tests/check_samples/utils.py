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

from tests.functional import utils


DEPLOYMENT_FILE = "/tmp/rally_functests_main_deployment.json"


class Rally(utils.Rally):

    def __init__(self, force_new_db=False):
        self._DEPLOYMENT_CREATE_ARGS = " --file %s" % DEPLOYMENT_FILE
        if not os.path.exists(DEPLOYMENT_FILE):
            subprocess.call(["rally", "--log-file", "/dev/null",
                             "deployment", "config"],
                            stdout=open(DEPLOYMENT_FILE, "w"))
        super(Rally, self).__init__(force_new_db=force_new_db)
