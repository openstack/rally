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
import traceback

import mock

import rally
from rally import api
from rally.common.plugin import discover
from rally.common import yamlutils as yaml
from rally.task import engine
from tests.unit import test


class RallyJobsTestCase(test.TestCase):
    rally_jobs_path = os.path.join(
        os.path.dirname(rally.__file__), "..", "rally-jobs")

    @mock.patch("rally.task.engine.TaskEngine"
                "._validate_config_semantic")
    def test_schema_is_valid(
            self, mock_task_engine__validate_config_semantic):
        discover.load_plugins(os.path.join(self.rally_jobs_path, "plugins"))

        files = {f for f in os.listdir(self.rally_jobs_path)
                 if (os.path.isfile(os.path.join(self.rally_jobs_path, f)) and
                     f.endswith(".yaml") and not f.endswith("_args.yaml"))}

        # TODO(andreykurilin): figure out why it fails
        files -= {"rally-mos.yaml", "sahara-clusters.yaml"}

        for filename in files:
            full_path = os.path.join(self.rally_jobs_path, filename)

            with open(full_path) as task_file:
                try:
                    args_file = os.path.join(
                        self.rally_jobs_path,
                        filename.rsplit(".", 1)[0] + "_args.yaml")

                    args = {}
                    if os.path.exists(args_file):
                        args = yaml.safe_load(open(args_file).read())
                        if not isinstance(args, dict):
                            raise TypeError(
                                "args file %s must be dict in yaml or json "
                                "presenatation" % args_file)

                    task = api._Task.render_template(task_file.read(), **args)
                    task = yaml.safe_load(task)

                    eng = engine.TaskEngine(task, mock.MagicMock(),
                                            mock.Mock())
                    eng.validate()
                except Exception:
                    print(traceback.format_exc())
                    self.fail("Wrong task input file: %s" % full_path)
