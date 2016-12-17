# Copyright 2013: Mirantis Inc.
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
import os
import re
import threading
import time
import unittest

import mock

from tests.functional import utils


FAKE_TASK_UUID = "87ab639d-4968-4638-b9a1-07774c32484a"


class TaskTestCase(unittest.TestCase):

    def _get_sample_task_config(self):
        return {
            "Dummy.dummy_random_fail_in_atomic": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 100,
                        "concurrency": 5
                    }
                }
            ]
        }

    def _get_sample_task_config_v2(self):
        return {
            "version": 2,
            "title": "Dummy task",
            "tags": ["dummy", "functional_test"],
            "subtasks": [
                {
                    "title": "first-subtask",
                    "group": "Dummy group",
                    "description": "The first subtask in dummy task",
                    "tags": ["dummy", "functional_test"],
                    "run_in_parallel": False,
                    "workloads": [{
                        "name": "Dummy.dummy",
                        "args": {
                            "sleep": 0
                        },
                        "runner": {
                            "type": "constant",
                            "times": 10,
                            "concurrency": 2
                        },
                        "context": {
                            "users": {
                                "tenants": 3,
                                "users_per_tenant": 2
                            }
                        }
                    }]
                },
                {
                    "title": "second-subtask",
                    "group": "Dummy group",
                    "description": "The second subtask in dummy task",
                    "tags": ["dummy", "functional_test"],
                    "run_in_parallel": False,
                    "workloads": [{
                        "name": "Dummy.dummy",
                        "args": {
                            "sleep": 1
                        },
                        "runner": {
                            "type": "constant",
                            "times": 10,
                            "concurrency": 2
                        },
                        "context": {
                            "users": {
                                "tenants": 3,
                                "users_per_tenant": 2
                            }
                        }
                    }]
                }
            ]
        }

    def _get_deployment_uuid(self, output):
        return re.search(
            r"Using deployment: (?P<uuid>[0-9a-f\-]{36})",
            output).group("uuid")

    def test_status(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        self.assertIn("finished", rally("task status"))

    def test_detailed(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        detailed = rally("task detailed")
        self.assertIn("Dummy.dummy_random_fail_in_atomic", detailed)
        self.assertIn("dummy_fail_test (2)", detailed)
        detailed_iterations_data = rally("task detailed --iterations-data")
        self.assertIn(". dummy_fail_test (2)", detailed_iterations_data)
        self.assertNotIn("n/a", detailed_iterations_data)

    def test_detailed_with_errors(self):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy_exception": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    }
                }
            ]
        }
        config = utils.TaskConfig(cfg)
        output = rally("task start --task %s" % config.filename)
        uuid = re.search(
            r"(?P<uuid>[0-9a-f\-]{36}): started", output).group("uuid")
        output = rally("task detailed")
        self.assertIn("Task %s has 1 error(s)" % uuid, output)

    def test_detailed_no_atomic_actions(self):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 100,
                        "concurrency": 5
                    }
                }
            ]
        }
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        detailed = rally("task detailed")
        self.assertIn("Dummy.dummy", detailed)
        detailed_iterations_data = rally("task detailed --iterations-data")
        self.assertNotIn("n/a", detailed_iterations_data)

    def test_start_with_empty_config(self):
        rally = utils.Rally()
        config = utils.TaskConfig(None)
        with self.assertRaises(utils.RallyCliError) as err:
            rally("task start --task %s" % config.filename)
        self.assertIn("Input task is empty", err.exception.output)

    def test_results(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        self.assertIn("result", rally("task results"))

    def test_results_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task results --uuid %s" % FAKE_TASK_UUID)

    def test_abort_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task abort --uuid %s" % FAKE_TASK_UUID)

    def test_delete_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task delete --uuid %s" % FAKE_TASK_UUID)

    def test_detailed_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task detailed --uuid %s" % FAKE_TASK_UUID)

    def test_report_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task report --tasks %s" % FAKE_TASK_UUID)

    def test_sla_check_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task sla-check --uuid %s" % FAKE_TASK_UUID)

    def test_status_with_wrong_task_id(self):
        rally = utils.Rally()
        self.assertRaises(utils.RallyCliError,
                          rally, "task status --uuid %s" % FAKE_TASK_UUID)

    def _assert_html_report_libs_are_embedded(self, file_path, expected=True):

        embedded_signatures = ["Copyright (c) 2011-2014 Novus Partners, Inc.",
                               "AngularJS v1.3.3",
                               "Copyright (c) 2010-2015, Michael Bostock"]
        external_signatures = ["<script type=\"text/javascript\" src=",
                               "<link rel=\"stylesheet\" href="]
        html = open(file_path).read()
        result_embedded = all([sig in html for sig in embedded_signatures])
        result_external = all([sig in html for sig in external_signatures])
        self.assertEqual(expected, result_embedded)
        self.assertEqual(not expected, result_external)

    def test_report_one_uuid(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        rally("task report --out %s" % rally.gen_report_path(extension="html"))
        html_report = rally.gen_report_path(extension="html")
        self.assertTrue(os.path.exists(html_report))
        self._assert_html_report_libs_are_embedded(html_report, False)
        self.assertRaises(utils.RallyCliError,
                          rally, "task report --report %s" % FAKE_TASK_UUID)
        rally("task report --junit --out %s" %
              rally.gen_report_path(extension="junit"))
        self.assertTrue(os.path.exists(
            rally.gen_report_path(extension="junit")))
        self.assertRaises(utils.RallyCliError,
                          rally, "task report --report %s" % FAKE_TASK_UUID)

    def test_report_bunch_uuids(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        task_uuids = []
        for i in range(3):
            res = rally("task start --task %s" % config.filename)
            for line in res.splitlines():
                if "finished" in line:
                    task_uuids.append(line.split(" ")[1][:-1])
        html_report = rally.gen_report_path(extension="html")
        rally("task report --tasks %s --out %s" % (" ".join(task_uuids),
                                                   html_report))
        self.assertTrue(os.path.exists(html_report))
        self._assert_html_report_libs_are_embedded(html_report, False)

    def test_report_bunch_files(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        files = []
        for i in range(3):
            rally("task start --task %s" % config.filename)
            path = "/tmp/task_%d.json" % i
            files.append(path)
            if os.path.exists(path):
                os.remove(path)
            rally("task results", report_path=path, raw=True)

        html_report = rally.gen_report_path(extension="html")
        rally("task report --tasks %s --out %s" % (
              " ".join(files), html_report))
        self.assertTrue(os.path.exists(html_report))
        self._assert_html_report_libs_are_embedded(html_report, False)

    def test_report_one_uuid_one_file(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        task_result_file = "/tmp/report_42.json"
        if os.path.exists(task_result_file):
            os.remove(task_result_file)
        rally("task results", report_path=task_result_file, raw=True)

        task_run_output = rally(
            "task start --task %s" % config.filename).splitlines()
        for line in task_run_output:
            if "finished" in line:
                task_uuid = line.split(" ")[1][:-1]
                break
        else:
            return 1

        html_report = rally.gen_report_path(extension="html")
        rally("task report --tasks"
              " %s %s --out %s" % (task_result_file, task_uuid,
                                   html_report))
        self.assertTrue(os.path.exists(html_report))
        self.assertRaises(utils.RallyCliError,
                          rally, "task report --report %s" % FAKE_TASK_UUID)
        self._assert_html_report_libs_are_embedded(html_report, False)

    def test_report_one_uuid_with_static_libs(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        html_report = rally.gen_report_path(extension="html")
        rally("task report --out %s --html-static" % html_report)
        self.assertTrue(os.path.exists(html_report))
        self._assert_html_report_libs_are_embedded(html_report)

    def test_trends(self):
        cfg1 = {
            "Dummy.dummy": [
                {"runner": {"type": "constant", "times": 2,
                            "concurrency": 2}}],
            "Dummy.dummy_random_action": [
                {"args": {"actions_num": 4},
                 "runner": {"type": "constant", "times": 2, "concurrency": 2}},
                {"runner": {"type": "constant", "times": 2,
                            "concurrency": 2}}]}
        cfg2 = {
            "Dummy.dummy": [
                {"args": {"sleep": 0.6},
                 "runner": {"type": "constant", "times": 2,
                            "concurrency": 2}}]}

        config1 = utils.TaskConfig(cfg1)
        config2 = utils.TaskConfig(cfg2)
        rally = utils.Rally()
        report = rally.gen_report_path(extension="html")

        for i in range(5):
            rally("task start --task %(file)s --tag trends_run_%(idx)d"
                  % {"file": config1.filename, "idx": i})
        rally("task start --task %s --tag trends_run_once" % config2.filename)

        tasks_list = rally("task list")
        uuids = [u[2:38] for u in tasks_list.split("\n") if "trends_run" in u]

        rally("task trends %(uuids)s --out %(report)s"
              % {"uuids": " ".join(uuids), "report": report})
        del config1, config2
        self.assertTrue(os.path.exists(report))

    def test_delete(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)

        rally("task list")

        self.assertIn("finished", rally("task status"))
        rally("task delete")

        self.assertNotIn("finished", rally("task list"))

    def test_list(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)

        self.assertIn("finished", rally("task list --deployment MAIN"))

        self.assertIn("There are no tasks",
                      rally("task list --status failed"))

        self.assertIn("finished", rally("task list --status finished"))

        self.assertIn(
            "deployment_name", rally("task list --all-deployments"))

        self.assertRaises(utils.RallyCliError,
                          rally, "task list --status not_existing_status")

    def test_list_with_print_uuids_option(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)

        # Validate against zero tasks
        self.assertEqual("", rally("task list --uuids-only"))

        # Validate against a single task
        res = rally("task start --task %s" % config.filename)
        task_uuids = []
        for line in res.splitlines():
            if "finished" in line:
                task_uuids.append(line.split(" ")[1][:-1])
        self.assertGreater(len(task_uuids), 0)
        self.assertIn(task_uuids[0],
                      rally("task list --uuids-only --deployment MAIN"))

        # Validate against multiple tasks
        for i in range(2):
            rally("task start --task %s" % config.filename)
            self.assertIn("finished", rally("task list --deployment MAIN"))
        res = rally("task list --uuids-only --deployment MAIN")
        task_uuids = res.split()
        self.assertEqual(3, len(task_uuids))
        res = rally("task list --uuids-only --deployment MAIN "
                    "--status finished")
        for uuid in task_uuids:
            self.assertIn(uuid, res)

    def test_validate_is_valid(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        output = rally("task validate --task %s" % config.filename)
        self.assertIn("Task config is valid", output)

    def test_validate_is_invalid(self):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        cfg = {"invalid": "config"}
        config = utils.TaskConfig(cfg)
        self.assertRaises(utils.RallyCliError,
                          rally,
                          ("task validate --task %(task_file)s "
                           "--deployment %(deployment_id)s") %
                          {"task_file": config.filename,
                           "deployment_id": deployment_id})

    def test_start(self):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        cfg = self._get_sample_task_config()
        config = utils.TaskConfig(cfg)
        output = rally(("task start --task %(task_file)s "
                        "--deployment %(deployment_id)s") %
                       {"task_file": config.filename,
                        "deployment_id": deployment_id})
        result = re.search(
            r"(?P<task_id>[0-9a-f\-]{36}): started", output)
        self.assertIsNotNone(result)

    def test_validate_with_plugin_paths(self):
        rally = utils.Rally()
        plugin_paths = ("tests/functional/extra/fake_dir1/,"
                        "tests/functional/extra/fake_dir2/")
        task_file = "tests/functional/extra/test_fake_scenario.json"
        output = rally(("--plugin-paths %(plugin_paths)s "
                        "task validate --task %(task_file)s") %
                       {"task_file": task_file,
                        "plugin_paths": plugin_paths})

        self.assertIn("Task config is valid", output)

        plugin_paths = ("tests/functional/extra/fake_dir1/"
                        "fake_plugin1.py,"
                        "tests/functional/extra/fake_dir2/"
                        "fake_plugin2.py")
        task_file = "tests/functional/extra/test_fake_scenario.json"
        output = rally(("--plugin-paths %(plugin_paths)s "
                        "task validate --task %(task_file)s") %
                       {"task_file": task_file,
                        "plugin_paths": plugin_paths})

        self.assertIn("Task config is valid", output)

        plugin_paths = ("tests/functional/extra/fake_dir1/,"
                        "tests/functional/extra/fake_dir2/"
                        "fake_plugin2.py")
        task_file = "tests/functional/extra/test_fake_scenario.json"
        output = rally(("--plugin-paths %(plugin_paths)s "
                        "task validate --task %(task_file)s") %
                       {"task_file": task_file,
                        "plugin_paths": plugin_paths})

        self.assertIn("Task config is valid", output)

    def _test_start_abort_on_sla_failure_success(self, cfg, times):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        config = utils.TaskConfig(cfg)
        rally(("task start --task %(task_file)s "
               "--deployment %(deployment_id)s --abort-on-sla-failure") %
              {"task_file": config.filename,
               "deployment_id": deployment_id})
        results = json.loads(rally("task results"))
        iterations_completed = len(results[0]["result"])
        self.assertEqual(times, iterations_completed)

    def test_start_abort_on_sla_failure_success_constant(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": times,
                        "concurrency": 5
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                }
            ]
        }
        self._test_start_abort_on_sla_failure_success(cfg, times)

    def test_start_abort_on_sla_failure_success_serial(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "serial",
                        "times": times
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                }
            ]
        }
        self._test_start_abort_on_sla_failure_success(cfg, times)

    def test_start_abort_on_sla_failure_success_rps(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "rps",
                        "times": times,
                        "rps": 20
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                }
            ]
        }
        self._test_start_abort_on_sla_failure_success(cfg, times)

    def _test_start_abort_on_sla_failure(self, cfg, times):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        config = utils.TaskConfig(cfg)
        rally(("task start --task %(task_file)s "
               "--deployment %(deployment_id)s --abort-on-sla-failure") %
              {"task_file": config.filename,
               "deployment_id": deployment_id})
        results = json.loads(rally("task results"))
        self.assertEqual(1, len(results),
                         "Second subtask should not be started")
        iterations_completed = len(results[0]["result"])
        self.assertLess(iterations_completed, times)

    def test_start_abort_on_sla_failure_max_seconds_constant(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": times,
                        "concurrency": 5
                    },
                    "sla": {
                        "max_seconds_per_iteration": 0.01
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def test_start_abort_on_sla_failure_max_seconds_serial(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "serial",
                        "times": times
                    },
                    "sla": {
                        "max_seconds_per_iteration": 0.01
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def test_start_abort_on_sla_failure_max_seconds_rps(self):
        times = 100
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "rps",
                        "times": times,
                        "rps": 20
                    },
                    "sla": {
                        "max_seconds_per_iteration": 0.01
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def test_start_abort_on_sla_failure_max_failure_rate_constant(self):
        times = 100
        cfg = {
            "Dummy.dummy_exception": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": times,
                        "concurrency": 5
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def test_start_abort_on_sla_failure_max_failure_rate_serial(self):
        times = 100
        cfg = {
            "Dummy.dummy_exception": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "serial",
                        "times": times
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def test_start_abort_on_sla_failure_max_failure_rate_rps(self):
        times = 100
        cfg = {
            "Dummy.dummy_exception": [
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "rps",
                        "times": times,
                        "rps": 20
                    },
                    "sla": {
                        "failure_rate": {"max": 0.0}
                    }
                },
                {
                    "args": {
                        "sleep": 0.1
                    },
                    "runner": {
                        "type": "constant",
                        "times": 1,
                        "concurrency": 1
                    },
                }
            ]
        }
        self._test_start_abort_on_sla_failure(cfg, times)

    def _start_task_in_new_thread(self, rally, cfg, report_file):
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        config = utils.TaskConfig(cfg)
        cmd = (("task start --task %(task_file)s "
                "--deployment %(deployment_id)s") %
               {"task_file": config.filename,
                "deployment_id": deployment_id})
        report_path = os.path.join(
            os.environ.get("REPORTS_ROOT", "rally-cli-output-files"),
            "TaskTestCase", report_file)
        task = threading.Thread(target=rally, args=(cmd, ),
                                kwargs={"report_path": report_path})
        task.start()
        uuid = None
        while not uuid:
            if not uuid:
                uuid = utils.get_global("RALLY_TASK", rally.env)
                time.sleep(0.5)
        return task, uuid

    def test_abort(self):
        RUNNER_TIMES = 10
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 5
                    },
                    "runner": {
                        "type": "serial",
                        "times": RUNNER_TIMES
                    }
                }
            ]
        }
        rally = utils.Rally()
        task, uuid = self._start_task_in_new_thread(
            rally, cfg, "test_abort-thread_with_abort.txt")
        rally("task abort %s" % uuid)
        task.join()
        results = json.loads(rally("task results"))
        iterations_completed = len(results[0]["result"])
        # NOTE(msdubov): check that the task is really stopped before
        #                the specified number of iterations
        self.assertLess(iterations_completed, RUNNER_TIMES)
        self.assertIn("aborted", rally("task status"))
        report = rally.gen_report_path(extension="html")
        rally("task report --out %s" % report)

    def test_abort_soft(self):
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 2
                    },
                    "runner": {
                        "type": "serial",
                        "times": 3,
                    }
                },
                {
                    "runner": {
                        "type": "serial",
                        "times": 10,
                    }
                }
            ]
        }
        rally = utils.Rally()
        task, uuid = self._start_task_in_new_thread(
            rally, cfg, "test_abort_soft-thread_with_soft_abort.txt")
        rally("task abort --soft")
        task.join()
        results = json.loads(rally("task results"))
        iterations_completed = len(results[0]["result"])
        # NOTE(msdubov): check that the task is stopped after first runner
        #                benchmark finished all its iterations
        self.assertEqual(3, iterations_completed)
        # NOTE(msdubov): check that the next benchmark scenario is not started
        self.assertEqual(1, len(results))
        self.assertIn("aborted", rally("task status"))

    def test_use(self):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        config = utils.TaskConfig(self._get_sample_task_config())
        output = rally(("task start --task %(task_file)s "
                        "--deployment %(deployment_id)s") %
                       {"task_file": config.filename,
                        "deployment_id": deployment_id})
        result = re.search(
            r"(?P<uuid>[0-9a-f\-]{36}): started", output)
        uuid = result.group("uuid")
        rally("task use --task %s" % uuid)
        current_task = utils.get_global("RALLY_TASK", rally.env)
        self.assertEqual(uuid, current_task)

    def test_start_v2(self):
        rally = utils.Rally()
        deployment_id = utils.get_global("RALLY_DEPLOYMENT", rally.env)
        cfg = self._get_sample_task_config_v2()
        config = utils.TaskConfig(cfg)
        output = rally(("task start --task %(task_file)s "
                        "--deployment %(deployment_id)s") %
                       {"task_file": config.filename,
                        "deployment_id": deployment_id})
        result = re.search(
            r"(?P<task_id>[0-9a-f\-]{36}): started", output)
        self.assertIsNotNone(result)

    def test_export(self):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 100,
                        "concurrency": 5
                    }
                }
            ]
        }
        config = utils.TaskConfig(cfg)
        output = rally("task start --task %s" % config.filename)
        uuid = re.search(
            r"(?P<uuid>[0-9a-f\-]{36}): started", output).group("uuid")
        connection = (
            "file-exporter:///" + rally.gen_report_path(extension="json"))
        output = rally("task export --uuid %s --connection %s" % (
            uuid, connection))
        expected = (
            "Task %(uuid)s results was successfully exported to %("
            "connection)s using file-exporter plugin." % {
                "uuid": uuid,
                "connection": connection,
            })
        self.assertIn(expected, output)

    def test_export_with_wrong_connection(self):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy": [
                {
                    "runner": {
                        "type": "constant",
                        "times": 100,
                        "concurrency": 5
                    }
                }
            ]
        }
        config = utils.TaskConfig(cfg)
        output = rally("task start --task %s" % config.filename)
        uuid = re.search(
            r"(?P<uuid>[0-9a-f\-]{36}): started", output).group("uuid")
        connection = (
            "fake:///" + rally.gen_report_path(extension="json"))
        self.assertRaises(utils.RallyCliError,
                          rally,
                          "task export --uuid %s --connection %s" % (
                              uuid, connection))


class SLATestCase(unittest.TestCase):

    def _get_sample_task_config(self, max_seconds_per_iteration=4,
                                failure_rate_max=0):
        return {
            "KeystoneBasic.create_and_list_users": [
                {
                    "args": {
                        "enabled": True
                    },
                    "runner": {
                        "type": "constant",
                        "times": 5,
                        "concurrency": 5
                    },
                    "sla": {
                        "max_seconds_per_iteration": max_seconds_per_iteration,
                        "failure_rate": {"max": failure_rate_max}
                    }
                }
            ]
        }

    def test_sla_fail(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(max_seconds_per_iteration=0.001)
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        self.assertRaises(utils.RallyCliError, rally, "task sla-check")

    def test_sla_success(self):
        rally = utils.Rally()
        config = utils.TaskConfig(self._get_sample_task_config())
        rally("task start --task %s" % config.filename)
        rally("task sla-check")
        expected = [
            {"benchmark": "KeystoneBasic.create_and_list_users",
             "criterion": "failure_rate",
             "detail": mock.ANY,
             "pos": 0, "status": "PASS"},
            {"benchmark": "KeystoneBasic.create_and_list_users",
             "criterion": "max_seconds_per_iteration",
             "detail": mock.ANY,
             "pos": 0, "status": "PASS"}
        ]
        data = rally("task sla-check --json", getjson=True)
        self.assertEqual(expected, data)


class SLAExtraFlagsTestCase(unittest.TestCase):

    def test_abort_on_sla_fail(self):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy_exception": [
                {
                    "args": {},
                    "runner": {
                        "type": "constant",
                        "times": 5,
                        "concurrency": 5
                    },
                    "sla": {
                        "failure_rate": {"max": 0}
                    }
                }
            ]}
        config = utils.TaskConfig(cfg)
        rally("task start --task %s --abort-on-sla-failure" % config.filename)
        expected = [
            {"benchmark": "Dummy.dummy_exception",
             "criterion": "aborted_on_sla",
             "detail": "Task was aborted due to SLA failure(s).",
             "pos": 0, "status": "FAIL"},
            {"benchmark": "Dummy.dummy_exception",
             "criterion": "failure_rate",
             "detail": mock.ANY,
             "pos": 0, "status": "FAIL"}
        ]
        try:
            rally("task sla-check --json", getjson=True)
        except utils.RallyCliError as expected_error:
            self.assertEqual(json.loads(expected_error.output), expected)
        else:
            self.fail("`rally task sla-check` command should return non-zero "
                      "exit code")

    def _test_broken_context(self, runner):
        rally = utils.Rally()
        cfg = {
            "Dummy.dummy": [
                {
                    "args": {},
                    "runner": runner,
                    "context": {
                        "dummy_context": {"fail_setup": True}
                    }
                }
            ]}
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        expected = [
            {"benchmark": "Dummy.dummy",
             "criterion": "something_went_wrong",
             "detail": mock.ANY,
             "pos": 0, "status": "FAIL"}
        ]
        try:
            rally("task sla-check --json", getjson=True)
        except utils.RallyCliError as expected_error:
            self.assertEqual(json.loads(expected_error.output), expected)
        else:
            self.fail("`rally task sla-check` command should return non-zero "
                      "exit code")

    def test_broken_context_with_constant_runner(self):
        self._test_broken_context({"type": "constant",
                                   "times": 5,
                                   "concurrency": 5})

    def test_broken_context_with_rps_runner(self):
        self._test_broken_context({"type": "rps",
                                   "times": 5,
                                   "rps": 3,
                                   "timeout": 6})


class SLAPerfDegrTestCase(unittest.TestCase):

    def _get_sample_task_config(self, max_degradation=500):
        return {
            "Dummy.dummy_random_action": [
                {
                    "args": {
                        "actions_num": 5,
                        "sleep_min": 0.5,
                        "sleep_max": 2
                    },
                    "runner": {
                        "type": "constant",
                        "times": 10,
                        "concurrency": 5
                    },
                    "sla": {
                        "performance_degradation": {
                            "max_degradation": max_degradation
                        }
                    }
                }
            ]
        }

    def test_sla_fail(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(max_degradation=1)
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        self.assertRaises(utils.RallyCliError, rally, "task sla-check")

    def test_sla_success(self):
        rally = utils.Rally()
        config = utils.TaskConfig(self._get_sample_task_config())
        rally("task start --task %s" % config.filename)
        rally("task sla-check")
        expected = [
            {"benchmark": "Dummy.dummy_random_action",
             "criterion": "performance_degradation",
             "detail": mock.ANY,
             "pos": 0, "status": "PASS"},
        ]
        data = rally("task sla-check --json", getjson=True)
        self.assertEqual(expected, data)


class HookTestCase(unittest.TestCase):

    def setUp(self):
        super(HookTestCase, self).setUp()
        self.started = time.time()

    def _assert_results_time(self, results):
        for trigger_results in results:
            for result in trigger_results["results"]:
                started_at = result["started_at"]
                finished_at = result["finished_at"]
                self.assertIsInstance(started_at, float)
                self.assertGreater(started_at, self.started)
                self.assertIsInstance(finished_at, float)
                self.assertGreater(finished_at, self.started)
                self.assertGreater(finished_at, started_at)

    def _get_sample_task_config(self, cmd, description, runner):
        return {
            "Dummy.dummy": [
                {
                    "args": {
                        "sleep": 0.1,
                    },
                    "runner": runner,
                    "hooks": [
                        {
                            "name": "sys_call",
                            "description": description,
                            "args": cmd,
                            "trigger": {
                                "name": "event",
                                "args": {
                                    "unit": "iteration",
                                    "at": [5],
                                }
                            }
                        }
                    ]
                }
            ]
        }

    def _get_result(self, config, iterations=None, seconds=None, error=False):
        result = {"config": config, "results": [], "summary": {}}
        events = iterations if iterations else seconds
        event_type = "iteration" if iterations else "time"
        status = "failed" if error else "success"
        for i in range(len(events)):
            itr_result = {
                "finished_at": mock.ANY,
                "started_at": mock.ANY,
                "triggered_by": {"event_type": event_type, "value": events[i]},
                "status": status,
                "output": {
                    "additive": [],
                    "complete": [{"chart_plugin": "TextArea",
                                  "data": ["RetCode: %i" % error,
                                           "StdOut: (empty)",
                                           "StdErr: (empty)"],
                                  "description": "Args: %s" % config["args"],
                                  "title": "System call"}]}}
            if error:
                itr_result["error"] = {"etype": "n/a",
                                       "msg": "Subprocess returned 1",
                                       "details": "stdout: "}
            result["results"].append(itr_result)
        result["summary"][status] = len(events)
        return result

    def test_hook_result_with_constant_runner(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/true",
            description="event_hook",
            runner={"type": "constant", "times": 10, "concurrency": 3})
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]
        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5])]
        self.assertEqual(expected, hook_results)
        self._assert_results_time(hook_results)

    def test_hook_result_with_constant_for_duration_runner(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/true",
            description="event_hook",
            runner={"type": "constant_for_duration",
                    "concurrency": 3, "duration": 10})
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]
        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5])]
        self.assertEqual(expected, hook_results)
        self._assert_results_time(hook_results)

    def test_hook_result_with_rps_runner(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/true",
            description="event_hook",
            runner={"type": "rps", "rps": 3, "times": 10})
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]
        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5])]
        self.assertEqual(expected, hook_results)
        self._assert_results_time(hook_results)

    def test_hook_result_with_serial_runner(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/true",
            description="event_hook",
            runner={"type": "serial", "times": 10})
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]
        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5])]
        self.assertEqual(expected, hook_results)
        self._assert_results_time(hook_results)

    def test_hook_result_error(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/false",
            description="event_hook",
            runner={"type": "constant", "times": 20, "concurrency": 3})
        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]
        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5], error=True)]
        self.assertEqual(expected, hook_results)
        self._assert_results_time(hook_results)

    def test_time_hook(self):
        rally = utils.Rally()
        cfg = self._get_sample_task_config(
            cmd="/bin/true",
            description="event_hook",
            runner={"type": "constant_for_duration",
                    "concurrency": 3, "duration": 10})
        cfg["Dummy.dummy"][0]["hooks"].append({
            "name": "sys_call",
            "description": "time_hook",
            "args": "/bin/true",
            "trigger": {
                "name": "event",
                "args": {
                    "unit": "time",
                    "at": [3, 6, 9],
                }
            }
        })

        config = utils.TaskConfig(cfg)
        rally("task start --task %s" % config.filename)
        results = json.loads(rally("task results"))
        hook_results = results[0]["hooks"]

        hooks_cfg = cfg["Dummy.dummy"][0]["hooks"]
        expected = [self._get_result(hooks_cfg[0], iterations=[5]),
                    self._get_result(hooks_cfg[1], seconds=[3, 6, 9])]
        self.assertEqual(
            expected,
            sorted(hook_results,
                   key=lambda i: i["config"]["trigger"]["args"]["unit"]))
        self._assert_results_time(hook_results)
