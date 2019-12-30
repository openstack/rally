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

import inspect
import itertools
import os
import traceback

import mock
import yaml

import rally
from rally import api
from rally.task import context
from rally.task import engine
from rally.task import scenario
from rally.task import task_cfg
from tests.unit import test

RALLY_PATH = os.path.dirname(os.path.dirname(rally.__file__))


class TaskSampleTestCase(test.TestCase):
    samples_path = os.path.join(RALLY_PATH, "samples", "tasks")

    def setUp(self):
        super(TaskSampleTestCase, self).setUp()
        if os.environ.get("TOX_ENV_NAME") == "cover":
            self.skipTest("There is no need to check samples in coverage job.")
        with mock.patch("rally.api.API.check_db_revision"):
            self.rapi = api.API()

    def iterate_samples(self, merge_pairs=True):
        """Iterates all task samples

        :param merge_pairs: Whether or not to return both json and yaml samples
            of one sample.
        """
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if filename.endswith("json") or (
                        not merge_pairs and filename.endswith("yaml")):
                    yield os.path.join(dirname, filename)

    def test_check_missing_sla_section(self):
        failures = []
        for path in self.iterate_samples():
            if "tasks/scenarios" not in path:
                continue
            with open(path) as task_file:
                task_config = yaml.safe_load(
                    self.rapi.task.render_template(
                        task_template=task_file.read()))
                for workload in itertools.chain(*task_config.values()):
                    if not workload.get("sla", {}):
                        failures.append(path)
        if failures:
            self.fail("One or several workloads from the list of samples below"
                      " doesn't have SLA section: \n  %s" %
                      "\n  ".join(failures))

    def test_schema_is_valid(self):
        scenarios = set()

        for path in self.iterate_samples():
            with open(path) as task_file:
                try:
                    try:
                        task_config = yaml.safe_load(
                            self.rapi.task.render_template(
                                task_template=task_file.read()))
                    except Exception:
                        print(traceback.format_exc())
                        self.fail("Invalid JSON file: %s" % path)
                    eng = engine.TaskEngine(task_cfg.TaskConfig(task_config),
                                            mock.MagicMock(), mock.Mock())
                    eng.validate(only_syntax=True)
                except Exception:
                    print(traceback.format_exc())
                    self.fail("Invalid task file: %s" % path)
                else:
                    scenarios.update(task_config.keys())

        missing = set(s.get_name() for s in scenario.Scenario.get_all())
        missing -= scenarios
        # check missing scenario is not from plugin
        missing = [s for s in list(missing)
                   if scenario.Scenario.get(s).__module__.startswith("rally")]
        self.assertEqual(missing, [],
                         "These scenarios don't have samples: %s" % missing)

    def test_task_config_pairs(self):

        not_equal = []
        missed = []
        checked = []

        for path in self.iterate_samples(merge_pairs=False):
            if path.endswith(".json"):
                json_path = path
                yaml_path = json_path.replace(".json", ".yaml")
            else:
                yaml_path = path
                json_path = yaml_path.replace(".yaml", ".json")

            if json_path in checked:
                continue
            else:
                checked.append(json_path)

            if not os.path.exists(yaml_path):
                missed.append(yaml_path)
            elif not os.path.exists(json_path):
                missed.append(json_path)
            else:
                with open(json_path) as json_file:
                    json_config = yaml.safe_load(
                        self.rapi.task.render_template(
                            task_template=json_file.read()))
                with open(yaml_path) as yaml_file:
                    yaml_config = yaml.safe_load(
                        self.rapi.task.render_template(
                            task_template=yaml_file.read()))
                if json_config != yaml_config:
                    not_equal.append("'%s' and '%s'" % (yaml_path, json_path))

        error = ""
        if not_equal:
            error += ("Sample task configs are not equal:\n\t%s\n"
                      % "\n\t".join(not_equal))
        if missed:
            self.fail("Sample task configs are missing:\n\t%s\n"
                      % "\n\t".join(missed))

        if error:
            self.fail(error)

    def test_no_underscores_in_filename(self):
        bad_filenames = []
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                if "_" in filename and (
                        filename.endswith(".yaml")
                        or filename.endswith(".json")):
                    full_path = os.path.join(dirname, filename)
                    bad_filenames.append(full_path)

        self.assertEqual([], bad_filenames,
                         "Following sample task filenames contain "
                         "underscores (_) but must use dashes (-) instead: "
                         "{}".format(bad_filenames))

    def test_context_samples_found(self):
        all_plugins = context.Context.get_all()
        context_samples_path = os.path.join(self.samples_path, "contexts")
        for p in all_plugins:
            # except contexts which belongs to tests module
            if not inspect.getfile(p).startswith(
               os.path.dirname(rally.__file__)):
                continue
            file_name = p.get_name().replace("_", "-")
            file_path = os.path.join(context_samples_path, file_name)
            if not os.path.exists("%s.json" % file_path):
                self.fail(("There is no json sample file of %s,"
                           "plugin location: %s" %
                           (p.get_name(), p.__module__)))
