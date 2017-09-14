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
import shutil
import tempfile
import traceback

import mock

import rally
from rally import api
from rally.common.plugin import discover
from rally.common import yamlutils as yaml
from rally.task import engine
from tests.unit import fakes
from tests.unit import test


class RallyJobsTestCase(test.TestCase):
    rally_jobs_path = os.path.join(
        os.path.dirname(rally.__file__), "..", "rally-jobs")

    def setUp(self):
        super(RallyJobsTestCase, self).setUp()
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp_dir, ".rally"))
        shutil.copytree(os.path.join(self.rally_jobs_path, "extra"),
                        os.path.join(self.tmp_dir, ".rally", "extra"))

        self.original_home = os.environ["HOME"]
        os.environ["HOME"] = self.tmp_dir

        def return_home():
            os.environ["HOME"] = self.original_home
        self.addCleanup(shutil.rmtree, self.tmp_dir)

        self.addCleanup(return_home)

    def test_schema_is_valid(self):
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
                                "presentation" % args_file)

                    task_inst = api._Task(api.API(skip_db_check=True))
                    task = task_inst.render_template(
                        task_template=task_file.read(), **args)
                    task = engine.TaskConfig(yaml.safe_load(task))
                    task_obj = fakes.FakeTask({"uuid": full_path})

                    eng = engine.TaskEngine(task, task_obj, mock.Mock())
                    eng.validate(only_syntax=True)
                except Exception:
                    print(traceback.format_exc())
                    self.fail("Wrong task input file: %s" % full_path)
