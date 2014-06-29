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
import rally.utils as rutils
import traceback

import yaml

from rally.benchmark import engine
from tests import test


class ScenarioTestCase(test.TestCase):
    rally_scenarios_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "rally-scenarios")

    @mock.patch("rally.benchmark.engine.BenchmarkEngine"
                "._validate_config_semantic")
    def test_schema_is_valid(self, mock_validate):
        rutils.load_plugins(os.path.join(self.rally_scenarios_path, "plugins"))

        for filename in ["rally.yaml", "rally-neutron.yaml"]:
            full_path = os.path.join(self.rally_scenarios_path, filename)

            with open(full_path) as task_file:
                try:
                    task_config = yaml.safe_load(task_file.read())
                    eng = engine.BenchmarkEngine(task_config,
                                                 mock.MagicMock())
                    eng.validate()
                except Exception:
                    print(traceback.format_exc())
                    self.fail("Wrong scenario config %s" % full_path)
