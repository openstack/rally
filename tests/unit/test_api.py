# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

"""Test for api."""

import copy
import os
from unittest import mock

import ddt

from rally import api
from rally.common import cfg
from rally.common import objects
from rally import consts
from rally import exceptions
from tests.unit import fakes
from tests.unit import test


FAKE_DEPLOYMENT_CONFIG = {
    # TODO(akscram): A fake engine is more suitable for that.
    "openstack": {
        "auth_url": "http://example.net:5000/v2.0/",
        "admin": {
            "username": "admin",
            "password": "myadminpass",
            "tenant_name": "demo",
            "domain_name": None,
            "project_domain_name": "Default",
            "user_domain_name": "Default",
            "profiler_hmac_key": None,
            "profiler_conn_str": None
        },
        "region_name": "RegionOne",
        "endpoint_type": consts.EndpointType.INTERNAL
    }
}


class APIGroupTestCase(test.TestCase):
    def setUp(self):
        super(APIGroupTestCase, self).setUp()
        mock_api = mock.Mock()
        self.apiGroup = api.APIGroup(mock_api)


@ddt.ddt
class TaskAPITestCase(test.TestCase):
    def setUp(self):
        super(TaskAPITestCase, self).setUp()
        self.task_uuid = "b0d9cd6c-2c94-4417-a238-35c7019d0257"
        self.task = {"uuid": self.task_uuid}
        mock_api = mock.Mock()
        mock_api.endpoint_url = None
        self.task_inst = api._Task(mock_api)

    @mock.patch("rally.api.task_cfg.TaskConfig")
    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate(self, mock_task_engine, mock_deployment_get, mock_task,
                      mock_task_config):
        fake_deployment = mock.Mock()
        fake_env = fake_deployment.env_obj
        mock_deployment_get.return_value = fake_deployment

        #######################################################################
        # The case #1 -- create temporary task
        #######################################################################
        self.task_inst.validate(deployment=fake_deployment.uuid,
                                config="config")

        mock_task_engine.assert_called_once_with(
            mock_task_config.return_value, mock_task.return_value,
            fake_env),
        mock_task_engine.return_value.validate.assert_called_once_with()

        mock_task.assert_called_once_with(
            temporary=True, env_uuid=fake_deployment.uuid)
        mock_deployment_get.assert_called_once_with(fake_deployment.uuid)
        self.assertFalse(mock_task.get.called)

        #######################################################################
        # The case #2 -- validate pre-created task
        #######################################################################
        mock_task_engine.reset_mock()
        mock_task.reset_mock()
        mock_deployment_get.reset_mock()

        fake_task = fakes.FakeTask(deployment_uuid="deployment_uuid_2")
        mock_task.get.return_value = fake_task

        task_uuid = "task-id"

        self.task_inst.validate(deployment=fake_deployment.uuid,
                                config="config",
                                task=task_uuid)

        mock_task_engine.assert_called_once_with(
            mock_task_config.return_value, fake_task, fake_env)
        mock_task_engine.return_value.validate.assert_called_once_with()

        self.assertFalse(mock_task.called)
        # check that deployment uuid is taken from task
        mock_deployment_get.assert_called_once_with(
            fake_task["deployment_uuid"])

        mock_task.get.assert_called_once_with(task_uuid)

        #######################################################################
        # The case #3 -- validate deprecated way for pre-created task
        #######################################################################
        mock_task_engine.reset_mock()
        mock_task.reset_mock()
        mock_deployment_get.reset_mock()

        task_instance = fakes.FakeTask(uuid="task-id")

        self.task_inst.validate(deployment=fake_deployment.uuid,
                                config="config",
                                task_instance=task_instance)

        mock_task_engine.assert_called_once_with(
            mock_task_config.return_value, fake_task, fake_env)
        mock_task_engine.return_value.validate.assert_called_once_with()

        self.assertFalse(mock_task.called)
        # check that deployment uuid is taken from task
        mock_deployment_get.assert_called_once_with(
            fake_task["deployment_uuid"])

        mock_task.get.assert_called_once_with(task_instance["uuid"])

        #######################################################################
        # The case #4 -- TaskConfig returns error
        #######################################################################
        mock_task_config.side_effect = Exception("Who is a good boy?! Woof.")

        e = self.assertRaises(exceptions.InvalidTaskException,
                              self.task_inst.validate,
                              deployment=fake_deployment.uuid,
                              config="config",
                              task_instance=task_instance)
        self.assertIn("Who is a good boy?! Woof.", "%s" % e)

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment",
                return_value=fakes.FakeDeployment(uuid="deployment_uuid"))
    @mock.patch("rally.api.engine.TaskEngine")
    def test_validate_engine_exception(self, mock_task_engine,
                                       mock_deployment, mock_task):
        excpt = exceptions.InvalidTaskException()
        mock_task_engine.return_value.validate.side_effect = excpt
        self.assertRaises(exceptions.InvalidTaskException,
                          self.task_inst.validate,
                          deployment=mock_deployment.return_value["uuid"],
                          config="config")

    def test_render_template(self):
        self.assertEqual(
            "3 = 3",
            self.task_inst.render_template(
                task_template="{{a + b}} = {{c}}", a=1, b=2, c=3))

    def test_render_template_default_values(self):
        template = "{% set a = a or 1 %}{{a + b}} = {{c}}"

        self.assertEqual("3 = 3",
                         self.task_inst.render_template(
                             task_template=template, b=2, c=3))

        self.assertEqual("5 = 5",
                         self.task_inst.render_template(
                             task_template=template, a=2, b=3, c=5))

    def test_render_template_default_filter(self):
        template = "{{ c | default(3) }}"

        self.assertEqual("3", self.task_inst.render_template(
            task_template=template))
        self.assertEqual("5", self.task_inst.render_template(
            task_template=template, c=5))

    def test_render_template_builtin(self):
        template = "{% for i in range(4) %}{{i}}{% endfor %}"

        self.assertEqual("0123", self.task_inst.render_template(
            task_template=template))

    def test_render_template_missing_args(self):
        self.assertRaises(TypeError, self.task_inst.render_template, "{{a}}")

    def test_render_template_include_other_template(self):
        other_template_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "samples/tasks/scenarios/dummy/dummy.json")
        template = "{%% include \"%s\" %%}" % os.path.basename(
            other_template_path)
        with open(other_template_path) as f:
            other_template = f.read()
        expect = self.task_inst.render_template(task_template=other_template)
        actual = self.task_inst.render_template(
            task_template=template,
            template_dir=os.path.dirname(other_template_path))
        self.assertEqual(expect, actual)

    def test_render_template_min(self):
        template = "{{ min(1, 2)}}"
        self.assertEqual("1", self.task_inst.render_template(
            task_template=template))

    def test_render_template_max(self):
        template = "{{ max(1, 2)}}"
        self.assertEqual("2", self.task_inst.render_template(
            task_template=template))

    def test_render_template_ceil(self):
        template = "{{ ceil(2.2)}}"
        self.assertEqual("3", self.task_inst.render_template(
            task_template=template))

    def test_render_template_round(self):
        template = "{{ round(2.2)}}"
        self.assertEqual("2", self.task_inst.render_template(
            task_template=template))

    @mock.patch("rally.common.objects.Deployment.get")
    @mock.patch("rally.common.objects.Task")
    def test_create(self, mock_task, mock_deployment_get):
        mock_deployment_get.return_value = {
            "uuid": "b0d9cd6c-2c94-4417-a238-35c7019d0257",
            "status": consts.DeployStatus.DEPLOY_FINISHED}
        tags = ["a"]
        self.task_inst.create(
            deployment=mock_deployment_get.return_value["uuid"], tags=tags)
        mock_task.assert_called_once_with(
            env_uuid=mock_deployment_get.return_value["uuid"],
            tags=tags)

    @mock.patch("rally.common.objects.Deployment.get",
                return_value={
                    "name": "xxx_name",
                    "uuid": "u_id",
                    "status": consts.DeployStatus.DEPLOY_INIT})
    def test_create_on_unfinished_deployment(self, mock_deployment_get):
        deployment_id = mock_deployment_get.return_value["uuid"]
        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.task_inst.create, deployment=deployment_id,
                          tags=["a"])

    @mock.patch("rally.api.task_cfg.TaskConfig")
    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    def test_start(self, mock_task_engine, mock_deployment_get,
                   mock_task, mock_task_config):
        fake_task = fakes.FakeTask(uuid="some_uuid")
        fake_task.get_status = mock.Mock()
        mock_task.return_value = fake_task
        fake_deployment = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED)
        mock_deployment_get.return_value = fake_deployment
        task_config_instance = mock_task_config.return_value

        self.assertEqual(
            (fake_task["uuid"], fake_task.get_status.return_value),
            self.task_inst.start(
                deployment=mock_deployment_get.return_value["uuid"],
                config="config")
        )

        mock_task_engine.assert_called_once_with(
            task_config_instance,
            mock_task.return_value,
            fake_deployment.env_obj,
            abort_on_sla_failure=False
        )
        task_engine = mock_task_engine.return_value
        task_engine.validate.assert_called_once_with()
        task_engine.run.assert_called_once_with()

        mock_task.assert_called_once_with(
            deployment_uuid=mock_deployment_get.return_value["uuid"],
            title=task_config_instance.title,
            description=task_config_instance.description)

        mock_deployment_get.assert_called_once_with(
            mock_deployment_get.return_value["uuid"])

    @mock.patch("rally.api.objects.Deployment.get")
    def test_start_temporary_task(self, mock_deployment_get):
        fake_deployment = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED,
            name="foo")
        mock_deployment_get.return_value = fake_deployment
        fake_task = objects.Task(task={"deployment_uuid": "deployment_uuid",
                                       "uuid": "some_uuid"}, temporary=True)

        self.assertRaises(ValueError,
                          self.task_inst.start,
                          deployment=fake_deployment,
                          config="config", task=fake_task)

    @mock.patch("rally.api.objects.Task.get")
    @mock.patch("rally.api.objects.Deployment.get")
    def test_start_with_inconsistent_deployment(self, mock_deployment_get,
                                                mock_task_get):
        deployment_uuid = "deployment_uuid"
        fake_deployment = fakes.FakeDeployment(
            uuid=deployment_uuid, admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_INCONSISTENT,
            name="foo")
        mock_deployment_get.return_value = fake_deployment
        fake_task_dict = {"env_uuid": deployment_uuid,
                          "uuid": "some_uuid"}
        fake_task = objects.Task(task=fake_task_dict)
        mock_task_get.return_value = fake_task

        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.task_inst.start,
                          deployment=deployment_uuid,
                          config="config",
                          task=fake_task["uuid"])

    @mock.patch("rally.api.task_cfg.TaskConfig")
    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_start_exception(self, mock_conf, mock_task_engine,
                             mock_deployment_get, mock_task, mock_task_config):
        mock_deployment_get.return_value = fakes.FakeDeployment(
            status=consts.DeployStatus.DEPLOY_FINISHED,
            name="foo", uuid="deployment_uuid")
        mock_task.return_value.is_temporary = False
        mock_task_engine.return_value.run.side_effect = TypeError
        self.assertRaises(TypeError, self.task_inst.start,
                          deployment="deployment_uuid", config="config")

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.engine.TaskEngine")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_start_with_wrong_config(self, mock_conf, mock_task_engine,
                                     mock_deployment_get, mock_task):
        mock_deployment_get.return_value = {
            "status": consts.DeployStatus.DEPLOY_FINISHED}
        self.assertRaises(exceptions.InvalidTaskException,
                          self.task_inst.start,
                          deployment="deployment_uuid", config="config")

    @ddt.data(True, False)
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_with_waiting(self, soft, mock_task, mock_time):
        mock_task.get_status.side_effect = (
            consts.TaskStatus.INIT,
            consts.TaskStatus.VALIDATING,
            consts.TaskStatus.RUNNING,
            consts.TaskStatus.ABORTING,
            consts.TaskStatus.SOFT_ABORTING,
            consts.TaskStatus.ABORTED)

        some_uuid = "ca441749-0eb9-4fcc-b2f6-76d314c55404"

        self.task_inst.abort(task_uuid=some_uuid, soft=soft, wait=True)

        mock_task.get.assert_called_once_with(some_uuid)
        mock_task.get.return_value.abort.assert_called_once_with(soft=soft)
        self.assertEqual([mock.call(some_uuid)] * 6,
                         mock_task.get_status.call_args_list)
        self.assertTrue(mock_time.sleep.called)

    @ddt.data(True, False)
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_without_waiting(self, soft, mock_task, mock_time):
        some_uuid = "133695fb-400d-4988-859c-30bfaa0488ce"

        self.task_inst.abort(task_uuid=some_uuid, soft=soft, wait=False)

        mock_task.get.assert_called_once_with(some_uuid)
        mock_task.get.return_value.abort.assert_called_once_with(soft=soft)
        self.assertFalse(mock_task.get_status.called)
        self.assertFalse(mock_time.sleep.called)

    @mock.patch("rally.api.LOG")
    @mock.patch("rally.api.time")
    @mock.patch("rally.api.objects.Task")
    def test_abort_using_deprecated_async_argument(self, mock_task, mock_time,
                                                   mock_log):
        kwargs = {"async": True}
        self.task_inst.abort(task_uuid="133695fb-400d-4988-859c-30bfaa0488ce",
                             **kwargs)
        self.assertTrue(mock_log.warning.called)

    @ddt.data({"task_status": "strange value",
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.INIT,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.VALIDATING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.ABORTING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.SOFT_ABORTING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.RUNNING,
               "expected_status": consts.TaskStatus.FINISHED},
              {"task_status": consts.TaskStatus.ABORTED,
               "expected_status": None},
              {"task_status": consts.TaskStatus.FINISHED,
               "expected_status": None},
              {"task_status": consts.TaskStatus.CRASHED,
               "expected_status": None},
              {"task_status": "strange value",
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.INIT,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.VALIDATING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.RUNNING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.ABORTING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.SOFT_ABORTING,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.ABORTED,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.FINISHED,
               "force": True, "expected_status": None},
              {"task_status": consts.TaskStatus.CRASHED,
               "force": True, "expected_status": None})
    @ddt.unpack
    @mock.patch("rally.api.objects.Task.get_status")
    @mock.patch("rally.api.objects.Task.delete_by_uuid")
    def test_delete(self, mock_task_delete_by_uuid, mock_task_get_status,
                    task_status, expected_status, force=False, raises=None):
        mock_task_get_status.return_value = task_status
        self.task_inst.delete(task_uuid=self.task_uuid, force=force)
        if force:
            self.assertFalse(mock_task_get_status.called)
        else:
            mock_task_get_status.assert_called_once_with(self.task_uuid)
        mock_task_delete_by_uuid.assert_called_once_with(
            self.task_uuid,
            status=expected_status)

    @mock.patch("rally.api.texporter.TaskExporter")
    @mock.patch("rally.api.objects.Task.get")
    def test_export(self, mock_task_get, mock_task_exporter):
        tasks_id = ["uuid-1", "uuid-2"]
        tasks = [mock.Mock(), mock.Mock()]
        tasks[0].to_dict.return_value = {"uuid": "uuid-1"}
        tasks[1].to_dict.return_value = {"uuid": "uuid-2"}
        mock_task_get.side_effect = tasks
        output_type = mock.Mock()
        output_dest = mock.Mock()

        reporter = mock_task_exporter.get.return_value
        mock_task_exporter.validate.return_value = None

        self.assertEqual(mock_task_exporter.make.return_value,
                         self.task_inst.export(
                             tasks=tasks_id + [{"uuid": "uuid-3"}],
                             output_type=output_type,
                             output_dest=output_dest))
        mock_task_exporter.get.assert_called_once_with(output_type)

        mock_task_exporter.validate.assert_called_once_with(
            output_type, context={}, config={},
            plugin_cfg={"destination": output_dest},
            vtype="syntax")

        mock_task_exporter.make.assert_called_once_with(
            reporter,
            [t.to_dict.return_value for t in tasks] + [{"uuid": "uuid-3"}],
            output_dest, api=self.task_inst.api)
        self.assertEqual([mock.call(u, detailed=True) for u in tasks_id],
                         mock_task_get.call_args_list)

    @mock.patch("rally.api.objects.Task")
    def test_get_detailed(self, mock_task):
        mock_task.get.return_value = mock.Mock()
        task = mock_task.get.return_value
        self.assertEqual(
            task.to_dict.return_value,
            self.task_inst.get(task_id="task_uuid", detailed=True))
        mock_task.get.assert_called_once_with("task_uuid", detailed=True)
        self.assertFalse(task.extend_results.called)
        task.to_dict.assert_called_once_with()

    @mock.patch("rally.api.objects.Task")
    def test_list(self, mock_task):
        task = mock.Mock()
        task.to_dict.return_value = self.task
        mock_task.list.return_value = [task]
        tasks = self.task_inst.list()
        self.assertEqual([self.task], tasks)

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    def test_import_results(self, mock_deployment_get, mock_task):
        mock_deployment_get.return_value = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED)

        workload = {"name": "test_scenario",
                    "description": "scen-description",
                    "full_duration": 3,
                    "load_duration": 1,
                    "start_time": 23.77,
                    "position": 77,
                    "runner": {},
                    "runner_type": "",
                    "contexts": {},
                    "contexts_results": [],
                    "hooks": [],
                    "pass_sla": True,
                    "sla": {},
                    "sla_results": {"sla": [{"success": True}]},
                    "args": {},
                    "statistics": {},
                    "total_iteration_count": 3,
                    "failed_iteration_count": 0,
                    "data": ["data-raw"]}

        task_results = {"subtasks": [
            {"title": "subtask-title",
             "workloads": [workload]}]}

        self.assertEqual(
            mock_task.return_value.to_dict(),
            self.task_inst.import_results(
                deployment=mock_deployment_get.return_value["uuid"],
                task_results=task_results)
        )

        mock_task.assert_called_once_with(env_uuid="deployment_uuid",
                                          tags=None)
        mock_task.return_value.update_status.assert_has_calls(
            [mock.call(consts.TaskStatus.RUNNING),
             mock.call(consts.SubtaskStatus.FINISHED)]
        )
        mock_task.return_value.add_subtask.assert_called_once_with(
            title="subtask-title")
        sub_task = mock_task.return_value.add_subtask.return_value
        sub_task.add_workload.assert_called_once_with(
            name=workload["name"],
            description=workload["description"],
            position=workload["position"], runner=workload["runner"],
            runner_type=workload["runner_type"],
            contexts=workload["contexts"],
            sla=workload["sla"],
            hooks=workload["hooks"], args=workload["args"]
        )
        sub_task.update_status.assert_called_once_with(
            consts.SubtaskStatus.FINISHED)
        work_load = sub_task.add_workload.return_value
        work_load.add_workload_data.assert_called_once_with(
            0, {"raw": workload["data"]})
        work_load.set_results.assert_called_once_with(
            full_duration=workload["full_duration"],
            load_duration=workload["load_duration"],
            sla_results=workload["sla_results"]["sla"],
            contexts_results=workload["contexts_results"],
            hooks_results=workload["hooks"], start_time=workload["start_time"])

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    @mock.patch("rally.api.CONF")
    def test_import_results_chunk_size(self, mock_conf,
                                       mock_deployment_get,
                                       mock_task):
        mock_deployment_get.return_value = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED)

        workload = {"name": "test_scenario",
                    "description": "scen-description",
                    "full_duration": 3,
                    "load_duration": 1,
                    "start_time": 23.77,
                    "position": 77,
                    "runner": {},
                    "runner_type": "",
                    "contexts": {"foo": {"killall": False}},
                    "contexts_results": [],
                    "hooks": [],
                    "pass_sla": True,
                    "sla": {},
                    "sla_results": {"sla": [{"success": True}]},
                    "args": {},
                    "statistics": {},
                    "total_iteration_count": 3,
                    "failed_iteration_count": 0,
                    "data": [{"timestamp": 1},
                             {"timestamp": 2},
                             {"timestamp": 3}]}
        task_results = {"subtasks": [{"title": "scen-subtasks",
                                      "workloads": [workload]}]}
        mock_conf.raw_result_chunk_size = 2

        self.assertEqual(
            mock_task.return_value.to_dict(),
            self.task_inst.import_results(
                deployment=mock_deployment_get.return_value["uuid"],
                task_results=task_results)
        )

        mock_task.assert_called_once_with(env_uuid="deployment_uuid",
                                          tags=None)
        mock_task.return_value.update_status.assert_has_calls(
            [mock.call(consts.TaskStatus.RUNNING),
             mock.call(consts.SubtaskStatus.FINISHED)]
        )
        mock_task.return_value.add_subtask.assert_called_once_with(
            title=task_results["subtasks"][0]["title"])
        sub_task = mock_task.return_value.add_subtask.return_value
        sub_task.add_workload.assert_called_once_with(
            name=workload["name"],
            description=workload["description"],
            position=workload["position"],
            runner=workload["runner"],
            runner_type=workload["runner_type"],
            contexts=workload["contexts"],
            sla=workload["sla"],
            hooks=workload["hooks"],
            args=workload["args"]
        )
        sub_task.update_status.assert_called_once_with(
            consts.SubtaskStatus.FINISHED)
        work_load = sub_task.add_workload.return_value
        self.assertEqual(
            [mock.call(0, {"raw": [{"timestamp": 1}, {"timestamp": 2}]}),
             mock.call(1, {"raw": [{"timestamp": 3}]})],
            work_load.add_workload_data.call_args_list)
        work_load.set_results.assert_called_once_with(
            full_duration=workload["full_duration"],
            load_duration=workload["load_duration"],
            sla_results=workload["sla_results"]["sla"],
            contexts_results=workload["contexts_results"],
            hooks_results=workload["hooks"], start_time=workload["start_time"])

    @mock.patch("rally.api.objects.Deployment.get")
    def test_import_results_with_inconsistent_deployment(
            self, mock_deployment_get):
        fake_deployment = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_INCONSISTENT,
            name="foo")
        mock_deployment_get.return_value = fake_deployment

        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.task_inst.import_results,
                          deployment="deployment_uuid",
                          task_results={},
                          tags=["tag"])

    @mock.patch("rally.api.objects.Task")
    @mock.patch("rally.api.objects.Deployment.get")
    def test_import_results_with_error_data(
            self, mock_deployment_get, mock_task):
        mock_deployment_get.return_value = fakes.FakeDeployment(
            uuid="deployment_uuid", admin="fake_admin", users=["fake_user"],
            status=consts.DeployStatus.DEPLOY_FINISHED)
        mock_task.return_value.result_has_valid_schema = mock.MagicMock(
            return_value=False)

        task_results = {"subtasks": [{"title": "subtask-title",
                                      "workloads": [{"data": [{"a": 1}]}]
                                      }]}

        self.assertRaises(exceptions.RallyException,
                          self.task_inst.import_results,
                          deployment="deployment_uuid",
                          task_results=task_results)


class BaseDeploymentTestCase(test.TestCase):
    def setUp(self):
        super(BaseDeploymentTestCase, self).setUp()
        mock_api = mock.Mock()
        mock_api.endpoint_url = None
        self.deployment_inst = api._Deployment(mock_api)
        self.deployment_config = copy.deepcopy(FAKE_DEPLOYMENT_CONFIG)
        self.deployment_uuid = "599bdf1d-fe77-461a-a810-d59b1490f4e3"
        admin_credential = copy.deepcopy(self.deployment_config["openstack"])
        admin_credential["endpoint"] = None
        admin_credential.update(admin_credential.pop("admin"))
        admin_credential["permission"] = consts.EndpointPermission.ADMIN
        admin_credential["https_insecure"] = False
        admin_credential["https_cacert"] = None
        self.credentials = {"admin": admin_credential, "users": []}
        self.deployment = {
            "uuid": self.deployment_uuid,
            "name": "fake_name",
            "config": self.deployment_config,
            "credentials": {"openstack": [self.credentials]}
        }


class DeploymentAPITestCase(BaseDeploymentTestCase):
    @mock.patch("rally.api.objects.Deployment")
    def test_create(self, mock_deployment):
        dep = self.deployment_inst.create(config=self.deployment_config,
                                          name="fake_deployment")
        self.assertEqual(mock_deployment.return_value.to_dict.return_value,
                         dep)
        mock_deployment.assert_called_once_with(
            name="fake_deployment",
            config=self.deployment_config,
            extras={})

    @mock.patch("rally.api.objects.Deployment")
    def test_create_duplicate(self, mock_deployment):

        exc = exceptions.DBRecordExists(
            field="name", value="fake_deployment", table="envs")

        mock_deployment.side_effect = exc

        a_exc = self.assertRaises(
            exceptions.DBRecordExists,
            self.deployment_inst.create, config=self.deployment_config,
            name="fake_deployment")
        self.assertEqual(exc, a_exc)

    @mock.patch("rally.api.objects.Deployment")
    def test_create_with_old_cfg(self, mock_deployment):
        mock_deployment.return_value.env_obj.spec = ""

        config = {"type": "ExistingCloud",
                  "creds": self.deployment_config}

        dep = self.deployment_inst.create(config=config,
                                          name="fake_deployment")
        self.assertEqual(mock_deployment.return_value.to_dict.return_value,
                         dep)
        mock_deployment.assert_called_once_with(
            name="fake_deployment",
            config=self.deployment_config,
            extras={})

        config = {"type": "Something",
                  "creds": self.deployment_config}

        e = self.assertRaises(
            exceptions.RallyException,
            self.deployment_inst.create, config=config,
            name="fake_deployment")
        self.assertIn("You are using deployment type which doesn't exist.",
                      "%s" % e)

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.get")
    def test_destroy(self, mock_env_manager_get):

        list_verifiers = [{"name": "f1", "uuid": "1"},
                          {"name": "f2", "uuid": "2"}]
        self.deployment_inst.api.verifier.list.return_value = list_verifiers

        self.deployment_inst.destroy(deployment=self.deployment_uuid)

        mock_env_manager_get.assert_called_once_with(self.deployment_uuid)
        mock_env_manager_get.return_value.destroy.assert_called_once_with(
            skip_cleanup=True
        )

    def test_recreate(self):
        e = self.assertRaises(exceptions.RallyException,
                              self.deployment_inst.recreate, deployment="")
        self.assertIn("Sorry, but recreate method", "%s" % e)

    @mock.patch("rally.common.objects.deploy.env_mgr.EnvManager.get")
    def test_get(self, mock_env_manager_get):
        origin_config = copy.deepcopy(self.deployment_config)
        mock_env_manager_get.return_value.data = {
            "spec": self.deployment_config,
            "platforms": {},
            "id": self.id(),
            "uuid": self.deployment["uuid"],
            "extras": {},
            "name": self.deployment["name"],
            "created_at": mock.Mock(),
            "updated_at": mock.Mock()}
        ret = self.deployment_inst.get(deployment=self.deployment["uuid"])
        for key in self.deployment:
            self.assertIn(key, ret)
            if key not in ("credentials", "config"):
                self.assertEqual(self.deployment[key], ret[key],
                                 "The key '%s' differs." % key)
        self.assertEqual(origin_config, ret["config"])

    @mock.patch("rally.common.objects.Deployment.list")
    def test_list(self, mock_deployment_list):
        mock_deployment = mock.Mock()
        mock_deployment.to_dict.return_value = self.deployment
        mock_deployment_list.return_value = [mock_deployment]
        ret = self.deployment_inst.list()
        for key in self.deployment:
            self.assertEqual(ret[0][key], self.deployment[key])

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check(self, mock_deployment_get):
        env = mock_deployment_get.return_value.env_obj
        env.check_health.return_value = {
            "foo": {"available": True}
        }

        self.assertEqual(
            {"foo": [{"services": []}]},
            self.deployment_inst.check(deployment="uuid"))
        env.check_health.assert_called_once_with()
        self.assertFalse(env.get_info.called)

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check_list_services(self, mock_deployment_get):
        env = mock_deployment_get.return_value.env_obj
        env.get_info.return_value = {
            "existing@openstack": {"info": {
                "services": [{"type": "foo", "name": "bar"},
                             {"type": "volumev4"}]}}
        }
        env.check_health.return_value = {
            "existing@openstack": {"available": True}
        }

        self.assertEqual(
            {"openstack": [{
                "services": [{"type": "foo", "name": "bar"},
                             {"type": "volumev4", "name": "__unknown__"}]}]},
            self.deployment_inst.check(deployment="uuid"))
        env.check_health.assert_called_once_with()
        env.get_info.assert_called_once_with()

    @mock.patch("rally.common.objects.Deployment.get")
    def test_deployment_check_fails(self, mock_deployment_get):
        env = mock_deployment_get.return_value.env_obj
        env.get_info.return_value = {
            "existing@openstack": {"info": {"services": [{"foo": "bar"}]}}
        }

        trace1 = ("Traceback (most recent call last):\n"
                  "  File '<ipython-input-3-e551aac575a4>', line 2, in "
                  "<module>\n"
                  "    raise Exception('asd: asd :asd asd ')\n"
                  "Exception: asd: asd :asd asd \n")
        msg1 = "Bad user creds: oops"
        trace2 = ("Traceback (most recent call last):\n"
                  "  File '<ipython-input-3-e551aac575a4>', line 2, in "
                  "<module>\n"
                  "    raise KeyError('asd: asd :asd asd2 ')\n"
                  "KeyError: asd: asd :asd asd2 \n")
        msg2 = "Ooops"
        env.check_health.return_value = {
            "existing@openstack": {
                "available": False,
                "message": msg1,
                "traceback": trace1},
            "foo@bar": {
                "available": False,
                "message": msg2,
                "traceback": trace2
            }
        }

        self.assertEqual(
            {
                "openstack": [{
                    "services": [],
                    "user_error": {"etype": "Exception",
                                   "msg": msg1,
                                   "trace": trace1}}],
                "foo@bar": [{
                    "services": [],
                    "admin_error": {"etype": "KeyError",
                                    "msg": msg2,
                                    "trace": trace2}}]},
            self.deployment_inst.check(deployment="uuid"))
        env.check_health.assert_called_once_with()
        self.assertFalse(env.get_info.called)


class APITestCase(test.TestCase):

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_config_args(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_isfile):
        api_ = api.API(config_args=["foo", "bar", "baz"])
        mock_conf.assert_called_once_with(
            ["foo", "bar", "baz"], default_config_files=None,
            project="rally", version="0.0.0")

        self.assertIsInstance(api_._deployment, api._Deployment)
        self.assertIsInstance(api_._task, api._Task)

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_config_file(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_isfile):
        api_ = api.API(config_file="myfile.conf")
        mock_conf.assert_called_once_with(
            [], default_config_files=["myfile.conf"],
            project="rally", version="0.0.0")

        self.assertIsInstance(api_._deployment, api._Deployment)
        self.assertIsInstance(api_._task, api._Task)

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_no_default_config_file(self, mock_conf, mock_version_string,
                                         mock_database_revision, mock_isfile):
        api.API(skip_db_check=True)
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile")
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_default_config_file(self, mock_conf, mock_version_string,
                                      mock_database_revision, mock_isfile):
        mock_isfile.side_effect = lambda f: f == "/etc/rally/rally.conf"
        api.API(skip_db_check=True)
        mock_conf.assert_called_once_with(
            [], default_config_files=["/etc/rally/rally.conf"],
            project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_exception(self, mock_conf, mock_version_string, mock_isfile):
        mock_conf.side_effect = cfg.ConfigFilesNotFoundError(["file1",
                                                              "file2"])
        self.assertRaises(exceptions.RallyException, api.API)
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.plugin.discover.load_plugins")
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "foobar", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_plugin_path(self, mock_conf, mock_version_string,
                              mock_database_revision, mock_load_plugins,
                              mock_isfile):
        mock_conf.__contains__.return_value = True
        mock_conf.get.side_effect = (
            lambda a: ["/path/from/args"] if a == "plugin_paths" else None)
        api.API(plugin_paths=["/my/path"])
        mock_conf.assert_called_once_with([], default_config_files=None,
                                          project="rally", version="0.0.0")
        mock_load_plugins.assert_has_calls([
            mock.call("/my/path"),
            mock.call("/path/from/args"),
        ])

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": "spam", "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_check_revision_exception(self, mock_conf,
                                           mock_version_string,
                                           mock_database_revision,
                                           mock_isfile):
        exc = self.assertRaises(exceptions.RallyException, api.API)
        self.assertIn("rally db upgrade", str(exc))
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    @mock.patch("os.path.isfile", return_value=False)
    @mock.patch("rally.common.version.database_revision",
                return_value={"revision": None, "current_head": "foobar"})
    @mock.patch("rally.common.version.version_string", return_value="0.0.0")
    @mock.patch("rally.api.CONF", spec=cfg.CONF)
    def test_init_check_revision_exception_no_db(self, mock_conf,
                                                 mock_version_string,
                                                 mock_database_revision,
                                                 mock_isfile):
        exc = self.assertRaises(exceptions.RallyException, api.API)
        self.assertIn("rally db create", str(exc))
        mock_conf.assert_called_once_with(
            [], default_config_files=None, project="rally", version="0.0.0")

    def test_version(self):
        api_inst = api.API(skip_db_check=True)
        self.assertEqual(1, api_inst.version)

    @mock.patch("requests.request")
    def test__request(self, mock_request):
        api_inst = api.API(skip_db_check=True)
        method = "test"
        path = "path"
        response = mock_request.return_value
        response.status_code = 200
        response.json.return_value = {"result": "test"}
        self.assertEqual("test", api_inst._request(path=path, method=method))

    @mock.patch("requests.request")
    @mock.patch("rally.exceptions.find_exception")
    def test__request_fail(self, mock_find_exception, mock_request):
        api_inst = api.API(skip_db_check=True)
        method = "test"
        path = "path"
        response = mock_request.return_value
        mock_find_exception.return_value = exceptions.RallyException()
        response.status_code = 201
        response.json.return_value = {"result": "test"}
        self.assertRaises(exceptions.RallyException,
                          api_inst._request, path=path, method=method)


class FakeVerifierManager(object):
    NAME = "fake_verifier"
    PLATFORM = "tests"
    TITLE = "Fake verifier which is used only for testing purpose"

    @classmethod
    def get_name(cls):
        return cls.NAME

    @classmethod
    def get_platform(cls):
        return cls.PLATFORM

    @classmethod
    def get_info(cls):
        return {"title": cls.TITLE}


class VerifierAPITestCase(test.TestCase):

    def setUp(self):
        super(VerifierAPITestCase, self).setUp()
        mock_api = mock.Mock()
        mock_api.endpoint_url = None
        self.verifier_inst = api._Verifier(mock_api)

    @mock.patch("rally.api.vmanager.VerifierManager.get_all")
    def test_list_plugins(self, mock_verifier_manager_get_all):
        platform = "some"
        mock_verifier_manager_get_all.return_value = [FakeVerifierManager]

        self.assertEqual(
            [{"name": FakeVerifierManager.NAME,
              "platform": FakeVerifierManager.PLATFORM,
              "description": FakeVerifierManager.TITLE,
              "location": "%s.%s" % (FakeVerifierManager.__module__,
                                     FakeVerifierManager.__name__)}],
            self.verifier_inst.list_plugins(platform=platform))
        mock_verifier_manager_get_all.assert_called_once_with(
            platform=platform)

    @mock.patch("rally.api.objects.Verifier.get")
    def test_get(self, mock_verifier_get):
        uuid = "some"

        self.assertEqual(mock_verifier_get.return_value.to_dict(),
                         self.verifier_inst.get(verifier_id=uuid))

        mock_verifier_get.assert_called_once_with(uuid)

    @mock.patch("rally.api.objects.Verifier.list")
    def test_list(self, mock_verifier_list):
        status = "some_special_status"
        mock_verifier_list.return_value = [mock.Mock()]

        self.assertEqual(
            [i.to_dict() for i in mock_verifier_list.return_value],
            self.verifier_inst.list(status=status))

        mock_verifier_list.assert_called_once_with(status)

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create(self, mock_verifier_manager_get, mock___verifier__get,
                    mock_verifier_create):
        mock___verifier__get.side_effect = exceptions.DBRecordNotFound(
            criteria="uuid: 1", table="verifiers")

        name = "SomeVerifier"
        vtype = "fake_verifier"
        platform = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        verifier_obj = mock_verifier_create.return_value
        verifier_obj.manager.get_platform.return_value = platform
        verifier_obj.manager._meta_get.side_effect = [source]

        verifier_uuid = self.verifier_inst.create(
            name=name, vtype=vtype, version=version,
            system_wide=system_wide, extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(vtype,
                                                          platform=None)
        mock___verifier__get.assert_called_once_with(name)
        mock_verifier_create.assert_called_once_with(
            name=name, source=None, system_wide=system_wide, version=version,
            vtype=vtype, platform=None, extra_settings=extra_settings)

        self.assertEqual(verifier_obj.uuid, verifier_uuid)
        verifier_obj.update_properties.assert_called_once_with(
            platform=platform, source=source)
        self.assertEqual([mock.call(consts.VerifierStatus.INSTALLING),
                          mock.call(consts.VerifierStatus.INSTALLED)],
                         verifier_obj.update_status.call_args_list)
        verifier_obj.manager.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create_fails_on_existing_verifier(
            self, mock_verifier_manager_get, mock___verifier__get,
            mock_verifier_create):
        name = "SomeVerifier"
        vtype = "fake_verifier"
        platform = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        self.assertRaises(exceptions.RallyException,
                          self.verifier_inst.create,
                          name=name, vtype=vtype, platform=platform,
                          source=source, version=version,
                          system_wide=system_wide,
                          extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(vtype,
                                                          platform=platform)
        mock___verifier__get.assert_called_once_with(name)
        self.assertFalse(mock_verifier_create.called)

    @mock.patch("rally.api.objects.Verifier.create")
    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.vmanager.VerifierManager.get")
    def test_create_fails_on_install_step(
            self, mock_verifier_manager_get, mock___verifier__get,
            mock_verifier_create):
        mock___verifier__get.side_effect = exceptions.DBRecordNotFound(
            criteria="id: 1", table="verifiers")
        verifier_obj = mock_verifier_create.return_value
        verifier_obj.manager.install.side_effect = RuntimeError

        name = "SomeVerifier"
        vtype = "fake_verifier"
        platform = "tests"
        source = "https://example.com"
        version = "3.1415"
        system_wide = True
        extra_settings = {"verifier_specific_option": "value_for_it"}

        self.assertRaises(RuntimeError,
                          self.verifier_inst.create,
                          name=name, vtype=vtype, platform=platform,
                          source=source, version=version,
                          system_wide=system_wide,
                          extra_settings=extra_settings)

        mock_verifier_manager_get.assert_called_once_with(
            vtype, platform=platform)
        mock___verifier__get.assert_called_once_with(name)
        mock_verifier_create.assert_called_once_with(
            name=name, source=source, system_wide=system_wide, version=version,
            vtype=vtype, platform=platform, extra_settings=extra_settings)

        self.assertEqual([mock.call(consts.VerifierStatus.INSTALLING),
                          mock.call(consts.VerifierStatus.FAILED)],
                         verifier_obj.update_status.call_args_list)
        verifier_obj.manager.install.assert_called_once_with()

    @mock.patch("rally.api.objects.Verifier.delete")
    @mock.patch("rally.common.objects.Verifier.get")
    def test_delete_no_verifications(self, mock_verifier_get,
                                     mock_verifier_delete):
        self.verifier_inst.api.verification.list
        self.verifier_inst.api.verification.list.return_value = []
        verifier_obj = mock_verifier_get.return_value

        verifier_id = "uuuiiiddd"
        deployment_id = "deployment"

        # remove just deployment specific data
        self.verifier_inst.delete(verifier_id=verifier_id,
                                  deployment_id=deployment_id)

        self.assertFalse(mock_verifier_delete.called)
        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=deployment_id)
        verifier_obj.set_env.assert_called_once_with(deployment_id)
        verifier_obj.manager.uninstall.assert_called_once_with()

        verifier_obj.set_env.reset_mock()
        verifier_obj.manager.uninstall.reset_mock()

        self.verifier_inst.api.verification.list.reset_mock()

        # remove the whole verifier
        self.verifier_inst.delete(verifier_id=verifier_id)

        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=None)
        self.assertFalse(verifier_obj.set_env.called)
        verifier_obj.manager.uninstall.assert_called_once_with(full=True)
        mock_verifier_delete.assert_called_once_with(verifier_id)

    @mock.patch("rally.common.objects.Verifier.get")
    @mock.patch("rally.api.objects.Verifier.delete")
    def test_delete_with_verifications(self,
                                       mock_verifier_delete,
                                       mock_verifier_get):
        verifications = [{"uuid": "uuid_1"}, {"uuid": "uuid_2"}]
        verifier_id = "uuuiiiddd"

        self.assertRaises(exceptions.RallyException,
                          self.verifier_inst.delete,
                          verifier_id=verifier_id)

        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=None)
        self.assertFalse(self.verifier_inst.api.verification.delete.called)

        self.verifier_inst.api.reset_mock()
        self.verifier_inst.api.verification.list.return_value = verifications

        self.verifier_inst.delete(verifier_id=verifier_id, force=True)
        self.verifier_inst.api.verification.list.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=None)
        self.assertEqual(
            [mock.call(verification_uuid=v["uuid"]) for v in verifications],
            self.verifier_inst.api.verification.delete.call_args_list)

    @mock.patch("rally.api.utils.BackupHelper")
    @mock.patch("rally.api._Verifier._get")
    def test_update_failed(self, mock___verifier__get, mock_backup_helper):
        verifier_obj = mock___verifier__get.return_value
        verifier_obj.system_wide = False
        uuid = "uuuuiiiidddd"
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              verifier_id=uuid)
        self.assertIn("At least one of the following parameters should be",
                      "%s" % e)
        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.update,
                                      verifier_id=uuid, system_wide=True)
                self.assertIn("because verifier is in '%s' status" % status,
                              "%s" % e)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        msg = "It is impossible to update the virtual environment for verifier"
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              verifier_id=uuid,
                              system_wide=True,
                              update_venv=True)
        self.assertIn(msg, "%s" % e)
        verifier_obj.system_wide = True
        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.update,
                              verifier_id=uuid, update_venv=True)
        self.assertIn(msg, "%s" % e)

    @mock.patch("rally.api.utils.BackupHelper")
    @mock.patch("rally.api._Verifier._get")
    def test_update(self, mock___verifier__get, mock_backup_helper):
        verifier_obj = mock___verifier__get.return_value
        verifier_obj.system_wide = False
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        uuid = "uuuuiiiidddd"
        version = "3.1415"

        # check updating just version
        self.verifier_inst.update(verifier_id=uuid, version=version)
        verifier_obj.manager.checkout.assert_called_once_with(version)
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, version=version)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        self.assertFalse(verifier_obj.manager.install_venv.called)

        verifier_obj.manager.checkout.reset_mock()
        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()

        # check system_wide
        self.verifier_inst.update(verifier_id=uuid,
                                  version=version, system_wide=True)

        verifier_obj.manager.checkout.assert_called_once_with(version)
        verifier_obj.manager.check_system_wide.assert_called_once_with()
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, version=version, system_wide=True)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        self.assertFalse(verifier_obj.manager.install_venv.called)

        verifier_obj.manager.checkout.reset_mock()
        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()

        # check switching from system-wide to virtual environment
        verifier_obj.system_wide = True

        self.verifier_inst.update(verifier_id=uuid, system_wide=False)
        verifier_obj.manager.install_venv.assert_called_once_with()
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, system_wide=False)

        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.install_venv.reset_mock()

        # check updating virtual environment
        verifier_obj.system_wide = False

        self.verifier_inst.update(verifier_id=uuid, update_venv=True)
        verifier_obj.manager.install_venv.assert_called_once_with()
        self.assertFalse(verifier_obj.manager.check_system_wide.called)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status)

        verifier_obj.manager.check_system_wide.reset_mock()
        verifier_obj.update_properties.reset_mock()
        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.install_venv.reset_mock()

        # check switching from virtual environment to system-wide
        verifier_obj.system_wide = False

        self.verifier_inst.update(verifier_id=uuid, system_wide=True)
        self.assertFalse(verifier_obj.manager.install_venv.called)
        verifier_obj.manager.check_system_wide.assert_called_once_with()
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        verifier_obj.update_properties.assert_called_once_with(
            status=verifier_obj.status, system_wide=True)

        verifier_obj.update_status.reset_mock()
        # check switching from system-wide to system-wide
        verifier_obj.system_wide = True
        self.verifier_inst.update(verifier_id=uuid, system_wide=True)
        verifier_obj.update_status.assert_called_once_with(
            consts.VerifierStatus.UPDATING)
        self.assertFalse(verifier_obj.manager.install_venv.called)

    @mock.patch("rally.api._Verifier._get")
    def test_configure_with_wrong_state_of_verifier(self,
                                                    mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.configure,
                                      verifier=verifier_id,
                                      deployment_id=deployment_id)
                self.assertIn("because verifier is in '%s' status" % status,
                              "%s" % e)

    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=False)
    @mock.patch("rally.api._Verifier._get")
    def test_configure_when_it_is_already_configured(self,
                                                     mock___verifier__get,
                                                     mock_is_debug):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        extra = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED

        # no recreate and no extra options
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=False))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        self.assertFalse(verifier_obj.manager.configure.called)
        self.assertFalse(verifier_obj.update_status.called)

        # no recreate, just extend existing configuration
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=False,
                             extra_options=extra))
        verifier_obj.manager.extend_configuration.assert_called_once_with(
            extra)
        self.assertFalse(verifier_obj.manager.configure.called)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

        # recreate with extra options
        self.assertEqual(verifier_obj.manager.configure.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=True,
                             extra_options=extra))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        verifier_obj.manager.configure.assert_called_once_with(
            extra_options=extra)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

    @mock.patch("rally.cli.commands.verify.logging.is_debug",
                return_value=True)
    @mock.patch("rally.api._Verifier._get")
    def test_configure_when_it_is_already_configured_with_logging(
            self, mock___verifier__get, mock_is_debug):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        extra = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED

        # no recreate and no extra options
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=False))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        self.assertFalse(verifier_obj.manager.configure.called)
        self.assertFalse(verifier_obj.update_status.called)

        # no recreate, just extend existing configuration
        self.assertEqual(verifier_obj.manager.get_configuration.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=False,
                             extra_options=extra))
        verifier_obj.manager.extend_configuration.assert_called_once_with(
            extra)
        self.assertFalse(verifier_obj.manager.configure.called)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

        # recreate with extra options
        self.assertEqual(verifier_obj.manager.configure.return_value,
                         self.verifier_inst.configure(
                             verifier=verifier_id,
                             deployment_id=deployment_id,
                             reconfigure=True,
                             extra_options=extra))
        self.assertFalse(verifier_obj.manager.extend_configuration.called)
        verifier_obj.manager.configure.assert_called_once_with(
            extra_options=extra)

        verifier_obj.update_status.reset_mock()
        verifier_obj.manager.extend_configuration.reset_mock()

    @mock.patch("rally.api._Verifier._get")
    def test_override_config_with_wrong_state_of_verifier(
            self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        new_content = {}

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(
                    exceptions.RallyException,
                    self.verifier_inst.override_configuration,
                    verifier_id=verifier_id, deployment_id=deployment_id,
                    new_configuration=new_content)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)

    @mock.patch("rally.api._Verifier._get")
    def test_override_config_when_it_is_already_configured(
            self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        deployment_id = "deployment"
        new_config = {"key": "value"}
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.override_configuration(
            verifier_id=verifier_id, deployment_id=deployment_id,
            new_configuration=new_config)
        verifier_obj.manager.override_configuration.assert_called_once_with(
            new_config)

    @mock.patch("rally.api._Verifier._get")
    def test_list_tests(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        pattern = "some"
        verifier_obj.status = consts.VerifierStatus.INIT

        e = self.assertRaises(exceptions.RallyException,
                              self.verifier_inst.list_tests,
                              verifier_id=verifier_id,
                              pattern=pattern)
        self.assertIn("because verifier %s is in '%s' status"
                      % (verifier_obj, verifier_obj.status), "%s" % e)
        self.assertFalse(verifier_obj.manager.list_tests.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.assertEqual(
            verifier_obj.manager.list_tests.return_value,
            self.verifier_inst.list_tests(verifier_id=verifier_id,
                                          pattern=pattern))
        verifier_obj.manager.list_tests.assert_called_once_with(pattern)

    @mock.patch("rally.api._Verifier._get")
    def test_add_extension(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        source = "example.com"
        version = 3.14159
        extra_settings = {}

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.add_extension,
                                      verifier_id=verifier_id,
                                      source=source, version=version,
                                      extra_settings=extra_settings)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.add_extension(
            verifier_id=verifier_id, source=source, version=version,
            extra_settings=extra_settings)
        verifier_obj.manager.install_extension.assert_called_once_with(
            source, version=version, extra_settings=extra_settings)
        self.assertEqual([mock.call(consts.VerifierStatus.EXTENDING),
                          mock.call(verifier_obj.status)],
                         verifier_obj.update_status.call_args_list)

        # check status will be updated in case of failure at installation step
        verifier_obj.update_status.reset_mock()

        verifier_obj.manager.install_extension.side_effect = RuntimeError
        self.assertRaises(RuntimeError,
                          self.verifier_inst.add_extension,
                          verifier_id=verifier_id,
                          source=source, version=version,
                          extra_settings=extra_settings)
        self.assertEqual([mock.call(consts.VerifierStatus.EXTENDING),
                          mock.call(verifier_obj.status)],
                         verifier_obj.update_status.call_args_list)

    @mock.patch("rally.api._Verifier._get")
    def test_list_extensions(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.list_extensions,
                                      verifier_id=verifier_id)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)
                self.assertFalse(verifier_obj.manager.list_extensions.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.assertEqual(verifier_obj.manager.list_extensions.return_value,
                         self.verifier_inst.list_extensions(
                             verifier_id=verifier_id))
        verifier_obj.manager.list_extensions.assert_called_once_with()

    @mock.patch("rally.api._Verifier._get")
    def test_delete_extension(self, mock___verifier__get):
        verifier_obj = mock___verifier__get.return_value
        verifier_id = "uuiiiidd"
        name = "some"

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verifier_inst.delete_extension,
                                      verifier_id=verifier_id, name=name)
                self.assertIn("because verifier %s is in '%s' status"
                              % (verifier_obj, status), "%s" % e)
                self.assertFalse(verifier_obj.manager.list_tests.called)

        verifier_obj.status = consts.VerifierStatus.INSTALLED
        self.verifier_inst.delete_extension(verifier_id=verifier_id,
                                            name=name)
        verifier_obj.manager.uninstall_extension.assert_called_once_with(name)


class VerificationAPITestCase(test.TestCase):

    results_data = {
        "totals": {"tests_count": 2,
                   "tests_duration": 4,
                   "success": 2,
                   "skipped": 0,
                   "expected_failures": 0,
                   "unexpected_success": 0,
                   "failures": 0},
        "tests": {
            "test_1": {
                "name": "test_1",
                "status": "success",
                "duration": 2,
                "tags": []}
        }
    }

    def setUp(self):
        super(VerificationAPITestCase, self).setUp()
        mock_api = mock.Mock()
        mock_api.endpoint_url = None
        self.verification_inst = api._Verification(mock_api)

    @mock.patch("rally.api.objects.Verification.get")
    def test_get(self, mock_verification_get):
        verification_uuid = "uuiiiidd"
        self.assertEqual(mock_verification_get.return_value.to_dict(),
                         self.verification_inst.get(
                             verification_uuid=verification_uuid))
        mock_verification_get.assert_called_once_with(verification_uuid)

    @mock.patch("rally.api.objects.Verification.get")
    def test_delete(self, mock_verification_get):
        verification_uuid = "uuiiiidd"
        self.verification_inst.delete(verification_uuid=verification_uuid)
        mock_verification_get.assert_called_once_with(verification_uuid)
        mock_verification_get.return_value.delete.assert_called_once_with()

    @mock.patch("rally.api.objects.Verification.list")
    def test_list(self, mock_verification_list):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        status = "some_status"

        mock_verification_list.return_value = [mock.Mock()]
        self.assertEqual(
            [i.to_dict() for i in mock_verification_list.return_value],
            self.verification_inst.list(
                verifier_id=verifier_id, deployment_id=deployment_id,
                tags=tags, status=status))
        mock_verification_list.assert_called_once_with(
            verifier_id, deployment_id=deployment_id, tags=tags,
            status=status)

    @mock.patch("rally.api.vreporter.VerificationReporter")
    @mock.patch("rally.api.objects.Verification.get")
    def test_report(self, mock_verification_get, mock_verification_reporter):
        verifications = ["uuid-1", "uuid-2"]
        output_type = mock.Mock()
        output_dest = mock.Mock()

        reporter = mock_verification_reporter.get.return_value

        self.assertEqual(mock_verification_reporter.make.return_value,
                         self.verification_inst.report(
                             uuids=verifications,
                             output_type=output_type,
                             output_dest=output_dest))
        mock_verification_reporter.get.assert_called_once_with(output_type)

        reporter.validate.assert_called_once_with(output_dest)

        mock_verification_reporter.make.assert_called_once_with(
            reporter, [mock_verification_get.return_value,
                       mock_verification_get.return_value],
            output_dest)
        self.assertEqual([mock.call(u) for u in verifications],
                         mock_verification_get.call_args_list)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api._Verifier._get")
    def test_import_results(self, mock___verifier__get,
                            mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        data = "contest of file with results"
        run_args = {"set_name": "compute"}

        # verifier_obj = mock___verifier__get.return_value
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.deployment = {
            "name": "deployment_name",
            "uuid": deployment_id}

        results = self.verification_inst.import_results(
            verifier_id=verifier_id, deployment_id=deployment_id,
            data=data, **run_args)

        verification = mock_verification_create.return_value

        self.assertEqual(verification.to_dict(), results["verification"])
        self.assertEqual(
            verifier_obj.manager.parse_results.return_value.totals,
            results["totals"])
        self.verification_inst.api.verifier._get.assert_called_once_with(
            verifier_id)
        verifier_obj.set_env.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate_args.assert_called_once_with(run_args)
        mock_verification_create.assert_called_once_with(
            verifier_id, deployment_id=deployment_id, run_args=run_args)
        verification.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)
        verifier_obj.manager.parse_results.assert_called_once_with(data)
        verification.finish.assert_called_once_with(results["totals"],
                                                    results["tests"])

        # check setting failed
        verification.finish.reset_mock()

        verifier_obj.manager.parse_results.side_effect = RuntimeError
        self.assertRaises(RuntimeError,
                          self.verification_inst.import_results,
                          verifier_id=verifier_id,
                          deployment_id=deployment_id,
                          data=data,
                          **run_args)
        self.assertFalse(verification.finish.called)
        self.assertTrue(verification.set_failed.called)

    @mock.patch("rally.api._Verifier._get")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_failed_due_to_wrong_status_of_verifier(
            self, mock_deployment_get, mock___verifier__get):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        verifier_obj = self.verification_inst.api.verifier._get.return_value

        for status in consts.VerifierStatus:
            if status != consts.VerifierStatus.INSTALLED:
                verifier_obj.status = status
                e = self.assertRaises(exceptions.RallyException,
                                      self.verification_inst.start,
                                      verifier_id=verifier_id,
                                      deployment_id=deployment_id)
                self.assertIn(
                    "Failed to start verification because verifier %s is in "
                    "'%s' status" % (verifier_obj, verifier_obj.status),
                    "%s" % e)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_with_configuring(self, mock_deployment_get,
                                    mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verifier_obj.deployment = {
            "name": "deployment_name",
            "uuid": "deployment_uuid",
            "status": consts.DeployStatus.DEPLOY_FINISHED}
        verifier_manager = mock.Mock()
        verifier_obj.manager = verifier_manager
        verifier_manager._meta_get.return_value = {}

        self.verification_inst.start(verifier_id=verifier_id,
                                     deployment_id=deployment_id)
        mock_deployment_get.assert_called_once_with(deployment_id)
        verifier_obj.set_env.assert_called_once_with(deployment_id)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api._Verifier.configure")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start(self, mock_deployment_get, mock_configure,
                   mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verification_obj = mock_verification_create.return_value
        verifier_obj.deployment = {"name": "deployment_name",
                                   "uuid": deployment_id}
        verifier_obj.manager._meta_get.return_value = {}

        self.verification_inst.start(verifier_id=verifier_id,
                                     deployment_id=deployment_id,
                                     tags=tags,
                                     **run_args)

        mock_deployment_get.assert_called_once_with(deployment_id)
        verifier_obj.set_env.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate.assert_called_once_with(run_args)

        mock_verification_create.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=deployment_id, tags=tags,
            run_args=run_args)
        verification_obj.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)

        context = {"config": verifier_obj.manager._meta_get.return_value,
                   "run_args": run_args,
                   "verification": verification_obj,
                   "verifier": verifier_obj}
        verifier_obj.manager.run.assert_called_once_with(context)

        results = verifier_obj.manager.run.return_value
        verification_obj.finish.assert_called_once_with(results.totals,
                                                        results.tests)

        self.assertFalse(mock_configure.called)

    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    name="xxx_name",
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_INIT))
    def test_start_on_unfinished_deployment(self, mock_deployment_get):
        verifier_id = "v_id"
        deployment_id = mock_deployment_get.return_value["uuid"]
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        self.assertRaises(exceptions.DeploymentNotFinishedStatus,
                          self.verification_inst.start,
                          verifier_id=verifier_id,
                          deployment_id=deployment_id,
                          tags=tags, **run_args)

    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.api.objects.Deployment.get",
                return_value=fakes.FakeDeployment(
                    uuid="deployment_uuid",
                    status=consts.DeployStatus.DEPLOY_FINISHED))
    def test_start_failed_to_run(self, mock_deployment_get,
                                 mock_verification_create):
        verifier_id = "vuuuiiddd"
        deployment_id = "duuuiidd"
        tags = ["foo", "bar"]
        run_args = {"arg": "value"}
        verifier_obj = self.verification_inst.api.verifier._get.return_value
        verifier_obj.deployment = {"name": "deployment_name",
                                   "uuid": deployment_id}
        verifier_obj.status = consts.VerifierStatus.INSTALLED
        verification_obj = mock_verification_create.return_value
        verifier_manager = mock.Mock()
        verifier_obj.manager = verifier_manager
        verifier_manager._meta_get.return_value = {}
        verifier_obj.manager.run.side_effect = RuntimeError

        self.assertRaises(RuntimeError,
                          self.verification_inst.start,
                          verifier_id=verifier_id,
                          deployment_id=deployment_id,
                          tags=tags, **run_args)

        verifier_obj.set_env.assert_called_once_with(deployment_id)
        verifier_obj.manager.validate.assert_called_once_with(run_args)
        mock_verification_create.assert_called_once_with(
            verifier_id=verifier_id, deployment_id=deployment_id, tags=tags,
            run_args=run_args)
        verification_obj.update_status.assert_called_once_with(
            consts.VerificationStatus.RUNNING)

        context = {"config": verifier_obj.manager._meta_get.return_value,
                   "run_args": run_args,
                   "verification": verification_obj,
                   "verifier": verifier_obj}
        verifier_obj.manager.run.assert_called_once_with(context)

        self.assertFalse(verification_obj.finish.called)

        self.assertFalse(
            self.verification_inst.api.verifier.configure.called)

    @mock.patch("rally.api._Verification.start")
    @mock.patch("rally.api._Deployment.get")
    @mock.patch("rally.api._Verification._get")
    def test_rerun(self, mock___verification__get, mock___deployment_get,
                   mock_start):

        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "fail"}}
        mock___verification__get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)
        self.verification_inst.api.deployment.get.return_value = {
            "name": "d_name",
            "uuid": "d_uuid"}
        mock___deployment_get.return_value = {"name": "d_name",
                                              "uuid": "d_uuid"}
        mock_start.return_value = (
            mock___verification__get.return_value,
            mock.Mock(totals=self.results_data["totals"],
                      tests=self.results_data["tests"]))

        self.verification_inst.rerun(verification_uuid="uuid",
                                     concurrency=1)
        mock_start.assert_called_once_with(
            verifier_id="v_uuid", deployment_id="d_uuid",
            load_list=list(tests.keys()), tags=None, concurrency=1)

    @mock.patch("rally.api._Verification.start")
    @mock.patch("rally.api.objects.Verification.create")
    @mock.patch("rally.common.objects.Verification.get")
    def test_rerun_failed_tests(self,
                                mock_verification_get,
                                mock_verification_create,
                                mock_start):
        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "fail"},
                 "test_3": {"status": "fail"}}
        mock_verification_get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)
        self.verification_inst.return_value = mock.Mock()
        self.verification_inst.api.deployment.get.return_value = {
            "name": "deployment_name",
            "uuid": "deployment_uuid",
        }
        expected_tests = [t for t, r in tests.items() if r["status"] == "fail"]
        self.verification_inst.rerun(verification_uuid="uuid", failed=True)
        mock_start.assert_called_once_with(
            verifier_id="v_uuid", deployment_id="deployment_uuid",
            load_list=expected_tests, tags=None)

    @mock.patch("rally.api._Verification._get")
    def test_rerun_failed_tests_raise_exc(
            self, mock___verification__get):
        tests = {"test_1": {"status": "success"},
                 "test_2": {"status": "success"},
                 "test_3": {"status": "skip"}}
        mock___verification__get.return_value = mock.Mock(
            uuid="uuid", verifier_uuid="v_uuid", deployment_uuid="d_uuid",
            tests=tests)

        e = self.assertRaises(exceptions.RallyException,
                              self.verification_inst.rerun,
                              verification_uuid="uuid",
                              failed=True)
        self.assertEqual("There are no failed tests from verification "
                         "(UUID=uuid).", "%s" % e)
