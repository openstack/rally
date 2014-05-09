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

    @mock.patch("rally.benchmark.engine.BenchmarkEngine"
                "._validate_config_semantic")
    def test_schema_is_valid(self, mock_semantic):
        samples_path = os.path.join(os.path.dirname(__file__), "..", "..",
                                    "doc", "samples", "tasks")

        scenarios = set()

        for dirname, dirnames, filenames in os.walk(samples_path):
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
