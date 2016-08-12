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

import json
import mock
import os
import re
import traceback

import yaml

from rally import api
from rally.task import scenario
from rally.task import engine
from tests.unit import test


class TaskSampleTestCase(test.TestCase):
    samples_path = os.path.join(
        os.path.dirname(__file__),
        os.pardir, os.pardir, os.pardir,
        "samples", "tasks")

    def setUp(self):
        super(TaskSampleTestCase, self).setUp()
        if os.environ.get("TOX_ENV_NAME") == "cover":
            self.skipTest("There is no need to check samples in coverage job.")

    @mock.patch("rally.task.engine.TaskEngine"
                "._validate_config_semantic")
    def test_schema_is_valid(self,
                             mock_task_engine__validate_config_semantic):
        scenarios = set()

        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                full_path = os.path.join(dirname, filename)

                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if not re.search("\.(ya?ml|json)$", filename, flags=re.I):
                    continue

                with open(full_path) as task_file:
                    try:
                        task_config = yaml.safe_load(api.Task.render_template
                                                     (task_file.read()))
                        eng = engine.TaskEngine(task_config,
                                                     mock.MagicMock())
                        eng.validate()
                    except Exception:
                        print(traceback.format_exc())
                        self.fail("Invalid task file: %s" % full_path)
                    else:
                        scenarios.update(task_config.keys())

        missing = set(s.get_name() for s in scenario.Scenario.get_all())
        missing -= scenarios
        # check missing scenario is not from plugin
        missing = [s for s in list(missing)
                   if scenario.Scenario.get(s).__module__.startswith("rally")]
        self.assertEqual(missing, [],
                         "These scenarios don't have samples: %s" % missing)

    def test_json_correct_syntax(self):
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                if not filename.endswith(".json"):
                    continue
                full_path = os.path.join(dirname, filename)
                with open(full_path) as task_file:
                    try:
                        json.loads(api.Task.render_template(task_file.read()))
                    except Exception:
                        print(traceback.format_exc())
                        self.fail("Invalid JSON file: %s" % full_path)

    def test_task_config_pair_existance(self):
        inexistent_paths = []

        for dirname, dirnames, filenames in os.walk(self.samples_path):
            # iterate over unique config names
            for sample_name in set(
                    f[:-5] for f in filenames
                    if f.endswith(".json") or f.endswith(".yaml")):

                partial_path = os.path.join(dirname, sample_name)
                yaml_path = partial_path + ".yaml"
                json_path = partial_path + ".json"

                if not os.path.exists(yaml_path):
                    inexistent_paths.append(yaml_path)
                elif not os.path.exists(json_path):
                    inexistent_paths.append(json_path)

        if inexistent_paths:
            self.fail("Sample task configs are missing:\n%r"
                      % inexistent_paths)

    def test_task_config_pairs_equality(self):
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            # iterate over unique config names
            for sample_name in set(
                    f[:-5] for f in filenames
                    if f.endswith(".json") or f.endswith(".yaml")):

                partial_path = os.path.join(dirname, sample_name)
                yaml_path = partial_path + ".yaml"
                json_path = partial_path + ".json"

                if os.path.exists(yaml_path) and os.path.exists(json_path):
                    with open(json_path) as json_file:
                        json_config = yaml.safe_load(api.Task.render_template
                                                     (json_file.read()))
                    with open(yaml_path) as yaml_file:
                        yaml_config = yaml.safe_load(api.Task.render_template
                                                     (yaml_file.read()))
                    self.assertEqual(json_config, yaml_config,
                                     "Sample task configs are not equal:"
                                     "\n%s\n%s" % (yaml_path, json_path))

    def test_no_underscores_in_filename(self):
        bad_filenames = []

        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                if "_" in filename and (filename.endswith(".yaml") or
                                        filename.endswith(".json")):
                    full_path = os.path.join(dirname, filename)
                    bad_filenames.append(full_path)

        self.assertEqual([], bad_filenames,
                         "Following sample task filenames contain "
                         "underscores (_) but must use dashes (-) instead: "
                         "{}".format(bad_filenames))
