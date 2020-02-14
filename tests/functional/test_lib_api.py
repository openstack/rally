# Copyright 2016: Mirantis Inc.
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

import testtools

from tests.functional import utils


class LibAPITestCase(testtools.TestCase):

    def test_rally_lib(self):
        rally = utils.Rally(force_new_db=True)
        cdir = os.path.dirname(os.path.realpath(__file__))
        app = os.path.join(cdir, "../ci/rally_app.py")
        subprocess.check_output(
            ["python", app, "--config-file", rally.config_filename])
