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

import mock
import os
import re
import traceback

import yaml

from rally.benchmark.scenarios import base
from rally.benchmark import engine
from tests import test


class TaskSampleTestCase(test.TestCase):
    samples_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "doc", "samples", "tasks")

    @mock.patch("rally.benchmark.engine.BenchmarkEngine"
                "._validate_config_semantic")
    def test_schema_is_valid(self, mock_semantic):
        scenarios = set()

        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                full_path = os.path.join(dirname, filename)

                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if not re.search('\.(ya?ml|json)$', filename, flags=re.I):
                    continue

                with open(full_path) as task_file:
                    try:
                        task_config = yaml.safe_load(task_file.read())
                        eng = engine.BenchmarkEngine(task_config,
                                                     mock.MagicMock())
                        eng.validate()
                    except Exception:
                        print(traceback.format_exc())
                        self.assertTrue(False,
                                        "Wrong task config %s" % full_path)
                    else:
                        scenarios.update(task_config.keys())

        # TODO(boris-42): We should refactor scenarios framework add "_" to
        #                 all non-benchmark methods.. Then this test will pass.
        missing = set(base.Scenario.list_benchmark_scenarios()) - scenarios
        self.assertEqual(missing, set([]),
                         "These scenarios don't have samples: %s" % missing)

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
            self.fail("Sample task configs are missing:\n%r" % inexistent_paths)

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
                        with open(yaml_path) as yaml_file:
                            json_config = yaml.safe_load(json_file.read())
                            yaml_config = yaml.safe_load(yaml_file.read())
                            self.assertEqual(
                                json_config,
                                yaml_config,
                                "Sample task configs are not equal:\n%s\n%s" %
                                (yaml_path, json_path))
