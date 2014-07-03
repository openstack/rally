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

import jsonschema
import mock

from rally.benchmark import engine
from rally import consts
from rally import exceptions
from tests import fakes
from tests import test


class BenchmarkEngineTestCase(test.TestCase):

    def test_init(self):
        config = mock.MagicMock()
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task)
        self.assertEqual(eng.config, config)
        self.assertEqual(eng.task, task)

    @mock.patch("rally.benchmark.engine.jsonschema.validate")
    def test_validate(self, mock_json_validate):
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

    @mock.patch("rally.benchmark.engine.jsonschema.validate")
    def test_validate__wrong_scenarios_name(self, mova_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock(
            side_effect=exceptions.NotFoundScenarios)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.benchmark.engine.jsonschema.validate")
    def test_validate__wrong_syntax(self, mova_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock()
        eng._validate_config_syntax = mock.MagicMock(
            side_effect=exceptions.InvalidBenchmarkConfig)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.benchmark.engine.jsonschema.validate")
    def test_validate__wrong_semantic(self, mova_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), task)
        eng._validate_config_scenarios_name = mock.MagicMock()
        eng._validate_config_syntax = mock.MagicMock()
        eng._validate_config_semantic = mock.MagicMock(
            side_effect=exceptions.InvalidBenchmarkConfig)

        self.assertRaises(exceptions.InvalidTaskException, eng.validate)
        self.assertTrue(task.set_failed.called)

    @mock.patch("rally.benchmark.engine.base_scenario.Scenario")
    def test__validate_config_scenarios_name(self, mock_scenario):
        config = {
            "a": [],
            "b": []
        }
        mock_scenario.list_benchmark_scenarios.return_value = ["e", "b", "a"]
        eng = engine.BenchmarkEngine(config, mock.MagicMock())
        eng._validate_config_scenarios_name(config)

    @mock.patch("rally.benchmark.engine.base_scenario.Scenario")
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

    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner.validate")
    @mock.patch("rally.benchmark.engine.base_ctx.ContextManager.validate")
    def test__validate_config_syntax(self, mock_context, mock_runner):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())
        eng._validate_config_syntax(config)
        mock_runner.assert_has_calls([mock.call({}), mock.call("b")])
        mock_context.assert_has_calls([mock.call("a", non_hidden=True),
                                       mock.call({}, non_hidden=True)])

    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner")
    @mock.patch("rally.benchmark.engine.base_ctx.ContextManager.validate")
    def test__validate_config_syntax__wrong_runner(self, mock_context,
                                                   mock_runner):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        mock_runner.validate = mock.MagicMock(
                side_effect=jsonschema.ValidationError("a"))
        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_syntax, config)

    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner.validate")
    @mock.patch("rally.benchmark.engine.base_ctx.ContextManager")
    def test__validate_config_syntax__wrong_context(self, mock_context,
                                                    mock_runner):
        config = {"sca": [{"context": "a"}], "scb": [{"runner": "b"}]}
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        mock_context.validate = mock.MagicMock(
                side_effect=jsonschema.ValidationError("a"))
        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_syntax, config)

    @mock.patch("rally.benchmark.engine.base_scenario.Scenario.validate")
    def test__validate_config_semantic_helper(self, mock_validate):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())
        eng._validate_config_semantic_helper("admin", "user", "name", "pos",
                                             task, {"args": "args"})
        mock_validate.assert_called_once_with(
            "name", "args", admin="admin", users=["user"],
            task=task)

    @mock.patch("rally.benchmark.engine.base_scenario.Scenario.validate")
    def test__validate_config_semanitc_helper_invalid_arg(self, mock_validate):
        mock_validate.side_effect = exceptions.InvalidScenarioArgument()
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_semantic_helper, "a", "u", "n",
                          "p", mock.MagicMock(), {})

    @mock.patch("rally.benchmark.engine.base_scenario.Scenario")
    @mock.patch(
        "rally.benchmark.engine.base_ctx.ContextManager.validate_semantic")
    def test__validate_config_semanitc_helper_invalid_context(self,
                                                              mock_validate_sm,
                                                              mock_scenario):
        mock_validate_sm.side_effect = exceptions.InvalidScenarioArgument()
        eng = engine.BenchmarkEngine(mock.MagicMock(), mock.MagicMock())

        self.assertRaises(exceptions.InvalidBenchmarkConfig,
                          eng._validate_config_semantic_helper, "a", "u", "n",
                          "p", mock.MagicMock(), {})

    @mock.patch("rally.benchmark.engine.osclients.Clients")
    @mock.patch("rally.benchmark.engine.users_ctx")
    @mock.patch("rally.benchmark.engine.BenchmarkEngine"
                "._validate_config_semantic_helper")
    def test__validate_config_semantic(self, mock_helper, mock_userctx,
                                       mock_osclients):
        mock_userctx.UserGenerator = fakes.FakeUserContext
        mock_osclients.return_value = mock.MagicMock()
        config = {
            "a": [mock.MagicMock(), mock.MagicMock()],
            "b": [mock.MagicMock()]
        }

        fake_task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, fake_task)

        eng.admin_endpoint = "admin"

        eng._validate_config_semantic(config)

        expected_calls = [
            mock.call("admin"),
            mock.call(fakes.FakeUserContext.user["endpoint"])
        ]
        mock_osclients.assert_has_calls(expected_calls)

        admin = user = mock_osclients.return_value
        expected_calls = [
            mock.call(admin, user, "a", 0, fake_task, config["a"][0]),
            mock.call(admin, user, "a", 1, fake_task, config["a"][1]),
            mock.call(admin, user, "b", 0, fake_task, config["b"][0])
        ]
        mock_helper.assert_has_calls(expected_calls)

    @mock.patch("rally.benchmark.engine.BenchmarkEngine.consume_results")
    def test_run__update_status(self, mock_consume):
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine([], task)
        eng.run()
        task.update_status.assert_has_calls([
            mock.call(consts.TaskStatus.RUNNING),
            mock.call(consts.TaskStatus.FINISHED)
        ])

    @mock.patch("rally.benchmark.engine.BenchmarkEngine.consume_results")
    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner")
    @mock.patch("rally.benchmark.engine.osclients")
    @mock.patch("rally.benchmark.engine.endpoint.Endpoint")
    def test_run__config_has_args(self, mock_endpoint, mock_osclients,
                                  mock_runner, mock_consume):
        config = {
            "a.args": [{"args": {"a": "a", "b": 1}}],
            "b.args": [{"args": {"a": 1}}]
        }
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task).bind([{}])
        eng.run()

    @mock.patch("rally.benchmark.engine.BenchmarkEngine.consume_results")
    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner")
    @mock.patch("rally.benchmark.engine.osclients")
    @mock.patch("rally.benchmark.engine.endpoint.Endpoint")
    def test_run__config_has_runner(self, mock_endpoint, mock_osclients,
                                    mock_runner, mock_consume):
        config = {
            "a.args": [{"runner": {"type": "a", "b": 1}}],
            "b.args": [{"runner": {"a": 1}}]
        }
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task).bind([{}])
        eng.run()

    @mock.patch("rally.benchmark.engine.BenchmarkEngine.consume_results")
    @mock.patch("rally.benchmark.engine.base_runner.ScenarioRunner")
    @mock.patch("rally.benchmark.engine.osclients")
    @mock.patch("rally.benchmark.engine.endpoint.Endpoint")
    def test_run__config_has_context(self, mock_endpoint, mock_osclients,
                                     mock_runner, mock_consume):
        config = {
            "a.args": [{"context": {"context_a": {"a": 1}}}],
            "b.args": [{"context": {"context_b": {"b": 2}}}]
        }
        task = mock.MagicMock()
        eng = engine.BenchmarkEngine(config, task).bind([{}])
        eng.run()

    @mock.patch("rally.benchmark.engine.osclients")
    @mock.patch("rally.benchmark.engine.endpoint.Endpoint")
    def test_bind(self, mock_endpoint, mock_osclients):
        mock_endpoint.return_value = mock.MagicMock()
        benchmark_engine = engine.BenchmarkEngine(mock.MagicMock(),
                                                  mock.MagicMock())
        endpoint = {
            "auth_url": "http://valid.com",
            "username": "user",
            "password": "pwd",
            "tenant_name": "tenant"
        }

        binded_benchmark_engine = benchmark_engine.bind([endpoint])
        self.assertEqual([mock_endpoint.return_value],
                         benchmark_engine.endpoints)
        self.assertEqual(benchmark_engine, binded_benchmark_engine)
        expected_calls = [
            mock.call.Clients(mock_endpoint.return_value),
            mock.call.Clients().verified_keystone()
        ]
        mock_osclients.assert_has_calls(expected_calls)
