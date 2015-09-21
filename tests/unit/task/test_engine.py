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

"""Tests for the Test engine."""

import collections
import copy

import jsonschema
import mock

from rally import consts
from rally import exceptions
from rally.task import engine
from tests.unit import fakes
from tests.unit import test


class TestException(exceptions.RallyException):
    msg_fmt = "TestException"


class BenchmarkEngineTestCase(test.TestCase):

    def test_init(self):
        config = mock.MagicMock()
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task)
        self.assertEqual(eng.config, config)
        self.assertEqual(eng.task, task)

    @mock.patch("rally.task.engine.jsonschema.validate")
    def test_validate(self, mock_validate):
        config = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, mock.MagicMock())
        mock_validate = mock.MagicMock()

        eng._validate_config_scenarios_name = mock_validate.names
        eng._validate_config_syntax = mock_validate.syntax
        eng._validate_config_semantic = mock_validate.semantic

        eng.validate()

        expected_calls = [
            mock.call.names(config),
            mock.call.syntax(config),
            mock.call.semantic(config)
        ]
        mock_validate.assert_has_calls(expected_calls)

    def test_validate__wrong_schema(self):
        config = {
            "wrong": True
        }
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task)
        self.assertRaises(exceptions.InvalidTaskException,
                          eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.task.engine.jsonschema.validate")
    def test_validate__wrong_scenarios_name(self, mock_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock(
            side_effect=exceptions.NotFoundScenarios)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.task.engine.jsonschema.validate")
    def test_validate__wrong_syntax(self, mock_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock()
        eng._validate_config_syntax = mock.MagicMock(
            side_effect=exceptions.InvalidBenchmarkConfig)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.task.engine.jsonschema.validate")
    def test_validate__wrong_semantic(self, mock_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock()
        eng._validate_config_syntax = mock.MagicMock()
        eng._validate_config_semantic = mock.MagicMock(
            side_effect=exceptions.InvalidBenchmarkConfig)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.task.engine.scenario.Scenario.get_all")
    def test__validate_config_scenarios_name(self, mock_scenario_get_all):
        config = {
            "a": [],
            "b": []
        }

        mock_scenario_get_all.return_value = [
            mock.MagicMock(get_name=lambda: "e"),
            mock.MagicMock(get_name=lambda: "b"),
            mock.MagicMock(get_name=lambda: "a")
        ]
        eng = engine.BenchmarkEngine(config, mock.MagicMock())
        eng._validate_config_scenarios_name(config)

    @mock.patch("rally.task.engine.scenario.Scenario")
    def test__validate_config_scenarios_name_non_exsisting(self,
                                                           mock_scenario):
        config = {
            "exist": [],
            "nonexist1": [],
            "nonexist2": []
        }
        mock_scenario.list_benchmark_scenarios.return_value = ["exist", "aaa"]
        eng = engine.BenchmarkEngine(config, mock.MagicMock())

        self.assertRaises(exceptions.NotFoundScenarios,
                          eng._validate_config_scenarios_name, config)

    @mock.patch("rally.task.engine.runner.ScenarioRunner.validate")
    @mock.patch("rally.task.engine.context.ContextManager.validate")
    def test__validate_config_syntax(
            self, mock_context_manager_validate,
            mock_scenario_runner_validate):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())
        eng._validate_config_syntax(config)
        mock_scenario_runner_validate.assert_has_calls(
            [mock.call({}), mock.call("b")], any_order=True)
        mock_context_manager_validate.assert_has_calls(
            [mock.call("a", non_hidden=True), mock.call({}, non_hidden=True)],
            any_order=True)

    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    @mock.patch("rally.task.engine.context.ContextManager.validate")
    def test__validate_config_syntax__wrong_runner(
            self, mock_context_manager_validate, mock_scenario_runner):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        mock_scenario_runner.validate = mock.MagicMock(
            side_effect=jsonschema.ValidationError("a"))
        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_syntax, config)

    @mock.patch("rally.task.engine.runner.ScenarioRunner.validate")
    @mock.patch("rally.task.engine.context.ContextManager")
    def test__validate_config_syntax__wrong_context(
            self, mock_context_manager, mock_scenario_runner_validate):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        mock_context_manager.validate = mock.MagicMock(
            side_effect=jsonschema.ValidationError("a"))
        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_syntax, config)

    @mock.patch("rally.task.engine.scenario.Scenario.validate")
    def test__validate_config_semantic_helper(self, mock_scenario_validate):
        deployment = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())
        eng._validate_config_semantic_helper("admin", "user", "name", "pos",
                                             deployment, {"args": "args"})
        mock_scenario_validate.assert_called_once_with(
            "name", {"args": "args"}, admin="admin", users=["user"],
            deployment=deployment)

    @mock.patch("rally.task.engine.scenario.Scenario.validate",
                side_effect=exceptions.InvalidScenarioArgument)
    def test__validate_config_semanitc_helper_invalid_arg(
            self, mock_scenario_validate):
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_semantic_helper, "a", "u", "n",
                          "p", mock.MagicMock(), {})

    @mock.patch("rally.task.engine.existing_users.ExistingUsers")
    def test_get_user_ctx_for_validation_existing_users(
            self, mock_existing_users):

        context = {"a": 10}
        users = [mock.MagicMock(), mock.MagicMock()]

        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock(),
                                     users=users)

        result = eng._get_user_ctx_for_validation(context)

        self.assertEqual(context["config"]["existing_users"], users)
        mock_existing_users.assert_called_once_with(context)

        self.assertEqual(mock_existing_users.return_value, result)

    @mock.patch("rally.task.engine.osclients.Clients")
    @mock.patch("rally.task.engine.users_ctx")
    @mock.patch("rally.task.engine.BenchmarkEngine"
                "._validate_config_semantic_helper")
    @mock.patch("rally.task.engine.objects.Deployment.get",
                return_value="FakeDeployment")
    def test__validate_config_semantic(
            self, mock_deployment_get,
            mock__validate_config_semantic_helper,
            mock_users_ctx, mock_clients):
        mock_users_ctx.UserGenerator = fakes.FakeUserContext
        mock_clients.return_value = mock.MagicMock()
        config = {
            "a": [mock.MagicMock(), mock.MagicMock()],
            "b": [mock.MagicMock()]
        }

        fake_task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, fake_task)

        eng.admin = "admin"

        eng._validate_config_semantic(config)

        expected_calls = [
            mock.call("admin"),
            mock.call(fakes.FakeUserContext.user["endpoint"])
        ]
        mock_clients.assert_has_calls(expected_calls)

        mock_deployment_get.assert_called_once_with(fake_task["uuid"])

        admin = user = mock_clients.return_value
        fake_deployment = mock_deployment_get.return_value
        expected_calls = [
            mock.call(admin, user, "a", 0, fake_deployment, config["a"][0]),
            mock.call(admin, user, "a", 1, fake_deployment, config["a"][1]),
            mock.call(admin, user, "b", 0, fake_deployment, config["b"][0])
        ]
        mock__validate_config_semantic_helper.assert_has_calls(
            expected_calls, any_order=True)

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    def test_run__update_status(
            self, mock_scenario_runner, mock_scenario,
            mock_context_manager_setup, mock_context_manager_cleanup,
            mock_result_consumer, mock_task_get_status):
        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.ABORTING
        eng = engine.BenchmarkEngine([], task)
        eng.run()
        task.update_status.assert_has_calls([
            mock.call(consts.TaskStatus.RUNNING),
            mock.call(consts.TaskStatus.FINISHED)
        ])

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    def test_run__config_has_args(
            self, mock_context_manager_setup, mock_context_manager_cleanup,
            mock_scenario_runner, mock_scenario,
            mock_result_consumer, mock_task_get_status):
        config = {
            "a.benchmark": [{"args": {"a": "a", "b": 1}}],
            "b.benchmark": [{"args": {"a": 1}}]
        }
        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.RUNNING
        eng = engine.BenchmarkEngine(config, task)
        eng.run()

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    def test_run__config_has_runner(
            self, mock_context_manager_setup, mock_context_manager_cleanup,
            mock_scenario_runner, mock_scenario, mock_result_consumer,
            mock_task_get_status):
        config = {
            "a.benchmark": [{"runner": {"type": "a", "b": 1}}],
            "b.benchmark": [{"runner": {"type": "c", "a": 1}}]
        }
        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.ABORTED
        eng = engine.BenchmarkEngine(config, task)
        eng.run()

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    def test_run__config_has_context(
            self, mock_context_manager_setup, mock_context_manager_cleanup,
            mock_scenario_runner, mock_scenario, mock_result_consumer,
            mock_task_get_status):
        config = {
            "a.benchmark": [{"context": {"context_a": {"a": 1}}}],
            "b.benchmark": [{"context": {"context_b": {"b": 2}}}]
        }
        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.RUNNING
        eng = engine.BenchmarkEngine(config, task)
        eng.run()

    @mock.patch("rally.task.engine.objects.task.Task.get_status")
    @mock.patch("rally.task.engine.LOG")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    def test_run_exception_is_logged(
            self, mock_context_manager_setup, mock_context_manager_cleanup,
            mock_scenario_runner, mock_scenario,
            mock_result_consumer, mock_log, mock_task_get_status):

        mock_context_manager_setup.side_effect = Exception

        mock_result_consumer.is_task_in_aborting_status.return_value = False
        config = {
            "a.benchmark": [{"context": {"context_a": {"a": 1}}}],
            "b.benchmark": [{"context": {"context_b": {"b": 2}}}]
        }
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task)

        eng.run()

        self.assertEqual(2, mock_log.exception.call_count)

    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    def test_run__task_soft_aborted(
            self, mock_scenario_runner, mock_scenario,
            mock_context_manager_setup, mock_context_manager_cleanup,
            mock_result_consumer):
        task = mock.MagicMock()
        mock_result_consumer.is_task_in_aborting_status.side_effect = [False,
                                                                       False,
                                                                       True]
        config = {
            "a.benchmark": [{"runner": {"type": "a", "b": 1}}],
            "b.benchmark": [{"runner": {"type": "a", "b": 1}}],
            "c.benchmark": [{"runner": {"type": "a", "b": 1}}]
        }
        fake_runner_cls = mock.MagicMock()
        fake_runner = mock.MagicMock()
        fake_runner_cls.return_value = fake_runner
        mock_scenario_runner.get.return_value = fake_runner_cls
        eng = engine.BenchmarkEngine(config, task)

        eng.run()

        self.assertEqual(2, fake_runner.run.call_count)
        self.assertEqual(mock.call(consts.TaskStatus.ABORTED),
                         task.update_status.mock_calls[-1])

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer")
    @mock.patch("rally.task.engine.context.ContextManager.cleanup")
    @mock.patch("rally.task.engine.context.ContextManager.setup")
    @mock.patch("rally.task.engine.scenario.Scenario")
    @mock.patch("rally.task.engine.runner.ScenarioRunner")
    def test_run__task_aborted(
            self, mock_scenario_runner, mock_scenario,
            mock_context_manager_setup, mock_context_manager_cleanup,
            mock_result_consumer, mock_task_get_status):
        task = mock.MagicMock()
        config = {
            "a.benchmark": [{"runner": {"type": "a", "b": 1}}],
            "b.benchmark": [{"runner": {"type": "a", "b": 1}}],
            "c.benchmark": [{"runner": {"type": "a", "b": 1}}]
        }
        fake_runner_cls = mock.MagicMock()
        fake_runner = mock.MagicMock()
        fake_runner_cls.return_value = fake_runner
        mock_task_get_status.return_value = consts.TaskStatus.SOFT_ABORTING
        mock_scenario_runner.get.return_value = fake_runner_cls
        eng = engine.BenchmarkEngine(config, task)
        eng.run()
        self.assertEqual(mock.call(consts.TaskStatus.ABORTED),
                         task.update_status.mock_calls[-1])

    @mock.patch("rally.task.engine.scenario.Scenario.get")
    def test__prepare_context(self, mock_scenario_get):
        default_context = {"a": 1, "b": 2}
        mock_scenario_get.return_value._meta_get.return_value = default_context
        task = mock.MagicMock()
        name = "a.benchmark"
        context = {"b": 3, "c": 4}
        endpoint = mock.MagicMock()
        config = {
            "a.benchmark": [{"context": {"context_a": {"a": 1}}}],
        }
        eng = engine.BenchmarkEngine(config, task)
        result = eng._prepare_context(context, name, endpoint)
        expected_context = copy.deepcopy(default_context)
        expected_context.setdefault("users", {})
        expected_context.update(context)
        expected_result = {
            "task": task,
            "admin": {"endpoint": endpoint},
            "scenario_name": name,
            "config": expected_context
        }
        self.assertEqual(result, expected_result)
        mock_scenario_get.assert_called_once_with(name)
        mock_scenario_get.return_value._meta_get.assert_called_once_with(
            "default_context"
        )

    @mock.patch("rally.task.engine.scenario.Scenario.get")
    def test__prepare_context_with_existing_users(self, mock_scenario_get):
        mock_scenario_get.return_value._meta_get.return_value = {}
        task = mock.MagicMock()
        name = "a.benchmark"
        context = {"b": 3, "c": 4}
        endpoint = mock.MagicMock()
        config = {
            "a.benchmark": [{"context": {"context_a": {"a": 1}}}],
        }
        existing_users = [mock.MagicMock()]
        eng = engine.BenchmarkEngine(config, task, users=existing_users)
        result = eng._prepare_context(context, name, endpoint)
        expected_context = {"existing_users": existing_users}
        expected_context.update(context)
        expected_result = {
            "task": task,
            "admin": {"endpoint": endpoint},
            "scenario_name": name,
            "config": expected_context
        }
        self.assertEqual(result, expected_result)
        mock_scenario_get.assert_called_once_with(name)
        mock_scenario_get.return_value._meta_get.assert_called_once_with(
            "default_context")


class ResultConsumerTestCase(test.TestCase):

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer.wait_and_abort")
    @mock.patch("rally.task.sla.SLAChecker")
    def test_consume_results(
            self, mock_sla_checker, mock_result_consumer_wait_and_abort,
            mock_task_get_status):
        mock_sla_instance = mock.MagicMock()
        mock_sla_checker.return_value = mock_sla_instance
        mock_task_get_status.return_value = consts.TaskStatus.RUNNING
        key = {"kw": {"fake": 2}, "name": "fake", "pos": 0}
        task = mock.MagicMock()
        runner = mock.MagicMock()
        runner.result_queue = collections.deque([1, 2])
        with engine.ResultConsumer(
                key, task, runner, False) as consumer_obj:
            pass

        expected_iteration_calls = [mock.call(1), mock.call(2)]
        self.assertEqual(expected_iteration_calls,
                         mock_sla_instance.add_iteration.mock_calls)
        self.assertEqual([1, 2], consumer_obj.results)

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.ResultConsumer.wait_and_abort")
    @mock.patch("rally.task.sla.SLAChecker")
    def test_consume_results_sla_failure_abort(
            self, mock_sla_checker, mock_result_consumer_wait_and_abort,
            mock_task_get_status):
        mock_sla_instance = mock.MagicMock()
        mock_sla_checker.return_value = mock_sla_instance
        mock_sla_instance.add_iteration.side_effect = [True, True, False,
                                                       False]
        key = {"kw": {"fake": 2}, "name": "fake", "pos": 0}
        task = mock.MagicMock()
        runner = mock.MagicMock()
        runner.result_queue = collections.deque([1, 2, 3, 4])

        with engine.ResultConsumer(key, task, runner, True):
            pass

        self.assertTrue(runner.abort.called)

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.threading.Thread")
    @mock.patch("rally.task.engine.threading.Event")
    @mock.patch("rally.task.sla.SLAChecker")
    def test_consume_results_abort_manually(self, mock_sla_checker,
                                            mock_event, mock_thread,
                                            mock_task_get_status):
        runner = mock.MagicMock(result_queue=False)

        is_done = mock.MagicMock()
        is_done.isSet.side_effect = (False, True)

        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.ABORTED

        key = {"kw": {"fake": 2}, "name": "fake", "pos": 0}

        eng = engine.BenchmarkEngine({}, task)
        eng.duration = 123
        eng.full_duration = 456

        with engine.ResultConsumer(key, task, runner, True):
            pass

        mock_sla_checker.assert_called_once_with(key["kw"])
        mocked_set_aborted = mock_sla_checker.return_value.set_aborted_manually
        mocked_set_aborted.assert_called_once_with()

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.sla.SLAChecker")
    def test_consume_results_sla_failure_continue(self, mock_sla_checker,
                                                  mock_task_get_status):
        mock_sla_instance = mock.MagicMock()
        mock_sla_checker.return_value = mock_sla_instance
        mock_task_get_status.return_value = consts.TaskStatus.FAILED
        mock_sla_instance.add_iteration.side_effect = [True, True, False,
                                                       False]
        key = {"kw": {"fake": 2}, "name": "fake", "pos": 0}
        task = mock.MagicMock()
        runner = mock.MagicMock()
        runner.result_queue = collections.deque([1, 2, 3, 4])

        with engine.ResultConsumer(key, task, runner, False):
            pass

        self.assertEqual(0, runner.abort.call_count)

    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.threading.Thread")
    @mock.patch("rally.task.engine.threading.Event")
    @mock.patch("rally.task.sla.SLAChecker")
    def test_comsume_results_with_unexpected_failure(self, mock_sla_checker,
                                                     mock_event, mock_thread,
                                                     mock_task_get_status):
        mock_sla_instance = mock.MagicMock()
        mock_sla_checker.return_value = mock_sla_instance
        key = {"kw": {"fake": 2}, "name": "fake", "pos": 0}
        task = mock.MagicMock()
        runner = mock.MagicMock()
        runner.result_queue = collections.deque([1])
        exc = TestException()
        try:
            with engine.ResultConsumer(key, task, runner, False):
                raise exc
        except TestException:
            pass

        mock_sla_instance.set_unexpected_failure.assert_has_calls(
            [mock.call(exc)])

    @mock.patch("rally.task.engine.threading.Thread")
    @mock.patch("rally.task.engine.threading.Event")
    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.BenchmarkEngine._prepare_context")
    @mock.patch("rally.task.engine.time.sleep")
    @mock.patch("rally.task.engine.BenchmarkEngine._get_runner")
    def test_wait_and_abort_on_abort(
            self, mock_benchmark_engine__get_runner,
            mock_sleep, mock_benchmark_engine__prepare_context,
            mock_task_get_status, mock_event, mock_thread):
        runner = mock.MagicMock()
        key = mock.MagicMock()
        task = mock.MagicMock()
        mock_task_get_status.side_effect = (consts.TaskStatus.RUNNING,
                                            consts.TaskStatus.RUNNING,
                                            consts.TaskStatus.ABORTING)
        mock_is_done = mock.MagicMock()
        mock_event.return_value = mock_is_done
        mock_is_done.isSet.return_value = False

        res = engine.ResultConsumer(key, task, runner, True)
        res.wait_and_abort()

        runner.abort.assert_called_with()
        # test task.get_status is checked until is_done is not set
        self.assertEqual(3, mock_task_get_status.call_count)

    @mock.patch("rally.task.engine.threading.Thread")
    @mock.patch("rally.task.engine.threading.Event")
    @mock.patch("rally.common.objects.Task.get_status")
    @mock.patch("rally.task.engine.BenchmarkEngine._prepare_context")
    @mock.patch("rally.task.engine.time.sleep")
    @mock.patch("rally.task.engine.BenchmarkEngine._get_runner")
    def test_wait_and_abort_on_no_abort(
            self, mock_benchmark_engine__get_runner, mock_sleep,
            mock_benchmark_engine__prepare_context, mock_task_get_status,
            mock_event, mock_thread):
        runner = mock.MagicMock()
        key = mock.MagicMock()
        task = mock.MagicMock()
        mock_task_get_status.return_value = consts.TaskStatus.RUNNING
        mock_is_done = mock.MagicMock()
        mock_event.return_value = mock_is_done

        mock_is_done.isSet.side_effect = [False, False, False, False, True]

        res = engine.ResultConsumer(key, task, runner, True)
        res.wait_and_abort()

        # check method don't abort runner if task is not aborted
        self.assertFalse(runner.abort.called)
        # test task.get_status is checked until is_done is not set
        self.assertEqual(4, mock_task_get_status.call_count)
