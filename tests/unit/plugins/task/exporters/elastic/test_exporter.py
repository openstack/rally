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

import copy
import json
from unittest import mock

import ddt

from rally import exceptions
from rally.plugins.task.exporters.elastic import exporter as elastic
from tests.unit import test


PATH = "rally.plugins.task.exporters.elastic.exporter"


class ValidatorTestCase(test.TestCase):
    @mock.patch("%s.client.ElasticSearchClient" % PATH)
    def test_validate(self, mock_elastic_search_client):
        validator = elastic.Validator()
        client = mock_elastic_search_client.return_value

        validator.validate({}, {}, None, {"destination": "/home/foo"})
        self.assertFalse(mock_elastic_search_client.called)

        client.version.return_value = "2.5.1"
        validator.validate({}, {}, None, {"destination": None})

        client.version.return_value = "5.6.2"
        validator.validate({}, {}, None, {"destination": None})

        client.version.return_value = "1.1.1"
        e = self.assertRaises(
            elastic.validation.ValidationError,
            validator.validate, {}, {}, None, {"destination": None})
        self.assertEqual("The unsupported version detected 1.1.1.",
                         e.message)

        exp_e = exceptions.RallyException("foo")
        client.version.side_effect = exp_e
        actual_e = self.assertRaises(
            elastic.validation.ValidationError,
            validator.validate, {}, {}, None, {"destination": None})
        self.assertEqual(exp_e.format_message(), actual_e.message)


def get_tasks_results():
    task_uuid = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"
    subtask_uuid = "35166362-0b11-4e74-929d-6988377e2da2"
    return [{
        "id": 1,
        "uuid": task_uuid,
        "deployment_uuid": "deployment-uuu-iii-iii-ddd",
        "env_uuid": "deployment-uuu-iii-iii-ddd",
        "env_name": "env-name",
        "title": "foo",
        "description": "bar",
        "status": "ok",
        "pass_sla": "yup",
        "task_duration": "dur",
        "tags": ["tag-1", "tag-2"],
        "subtasks": [{
            "task_uuid": task_uuid,
            "subtask_uuid": subtask_uuid,
            "workloads": [{
                "id": 3,
                "position": 0,
                "uuid": "4dcd88a5-164b-4431-8b44-3979868116dd",
                "task_uuid": task_uuid,
                "subtask_uuid": subtask_uuid,
                "name": "CinderVolumes.list_volumes",
                "args": {"key1": "value1"},
                "description": "List all volumes.",
                "runner_type": "constant",
                "runner": {"type": "constant",
                           "times": 3},
                "sla": {},
                "contexts": {"users@openstack": {"tenants": 2}},
                "created_at": "2017-07-28T23:35:46",
                "updated_at": "2017-07-28T23:37:55",
                "start_time": 1501284950.371992,
                "failed_iteration_count": 2,
                "load_duration": 97.82577991485596,
                "full_duration": 127.59103488922119,
                "pass_sla": False,
                "sla_results": {
                    "sla": [{"criterion": "JoGo",
                             "success": False,
                             "detail": "because i do not like you"}]
                },
                "statistics": {
                    "durations": {
                        "total": {
                            "data": {"success": "80.0%"}
                        }
                    }
                },
                "data": [
                    # iteration where the unwrapped action failed
                    {"timestamp": 1501284950.371992,
                     "error": ["ERROR!"],
                     "duration": 10.096552848815918,
                     "idle_duration": 0,
                     "atomic_actions": [
                         {"finished_at": 1501284961.468537,
                          "started_at": 1501284950.372052,
                          "name": "cinder.list_volumes",
                          "children": []}]},
                    # iteration where the known action failed
                    {"timestamp": 1501284950.371992,
                     "error": ["ERROR!"],
                     "duration": 10.096552848815918,
                     "idle_duration": 0,
                     "atomic_actions": [
                         {"finished_at": 1501284961.468537,
                          "started_at": 1501284950.372052,
                          "name": "cinder.list_volumes",
                          "failed": True,
                          "children": []}]}
                ]}]
        }]
    }]


@ddt.ddt
class ElasticSearchExporterTestCase(test.TestCase):
    def setUp(self):
        super(ElasticSearchExporterTestCase, self).setUp()
        self.patcher = mock.patch.object(elastic.client, "ElasticSearchClient")
        self.es_cls = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_init(self):
        exporter = elastic.ElasticSearchExporter([], "http://example.com")
        self.assertTrue(exporter._remote)
        self.assertEqual(self.es_cls.return_value,
                         getattr(exporter, "_client"))

        exporter = elastic.ElasticSearchExporter([], None)
        self.assertTrue(exporter._remote)
        self.assertEqual(self.es_cls.return_value,
                         getattr(exporter, "_client"))

        exporter = elastic.ElasticSearchExporter([], "/foo/bar")
        self.assertFalse(exporter._remote)
        self.assertIsNone(getattr(exporter, "_client", None))

    @ddt.data(None, "/home/bar", "https://example.com")
    def test__add_index(self, destination):

        index = "foo"
        doc_type = "bar"
        body = {
            "key1": "value1",
            "key2": "value2"
        }
        doc_id = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"

        exporter = elastic.ElasticSearchExporter([], destination)

        exporter._add_index(index=index,
                            body=body,
                            doc_id=doc_id,
                            doc_type=doc_type)

        self.assertEqual(2, len(exporter._report))
        self.assertEqual({"index": {"_index": index,
                                    "_type": doc_type,
                                    "_id": doc_id}},
                         json.loads(exporter._report[0]))

    @ddt.data(True, False)
    @mock.patch("%s.ElasticSearchExporter._add_index" % PATH)
    def test__process_atomic_actions(self, known_fail, mock__add_index):
        es_exporter = elastic.ElasticSearchExporter({}, None)

        itr_data = {"id": "foo_bar_uuid",
                    "error": ["I was forced to fail. Sorry"],
                    "timestamp": 1, "duration": 2, "idle_duration": 1}
        workload = {
            "scenario_cfg": ["key1=value1"],
            "runner_name": "foo",
            "runner_cfg": ["times=3"],
            "contexts": ["users@openstack.tenants=2"],
            "deployment_uuid": "dep_uuid", "deployment_name": "dep_name"}

        atomic_actions = [
            {"name": "do_something",
             "started_at": 1, "finished_at": 2,
             "children": []},
            {"name": "fail_something",
             "started_at": 3,
             "finished_at": 4,
             "children": [
                 {"name": "rm -rf", "started_at": 3, "finished_at": 4,
                  "children": []}
             ]},
        ]

        if known_fail:
            atomic_actions[-1]["failed"] = True
            atomic_actions[-1]["children"][-1]["failed"] = True

        es_exporter._process_atomic_actions(
            atomic_actions=atomic_actions, itr=itr_data,
            workload_id="wid", workload=workload)

        expected_calls = [
            mock.call(
                "rally_atomic_action_data_v1",
                {
                    "deployment_uuid": "dep_uuid",
                    "deployment_name": "dep_name",
                    "action_name": "do_something",
                    "scenario_cfg": ["key1=value1"],
                    "contexts": ["users@openstack.tenants=2"],
                    "runner_name": "foo",
                    "runner_cfg": ["times=3"],
                    "started_at": "1970-01-01T00:00:01",
                    "finished_at": "1970-01-01T00:00:02",
                    "duration": 1,
                    "success": True,
                    "error": None,
                    "parent": None,
                    "workload_uuid": "wid"},
                doc_id="foo_bar_uuid_action_do_something_0"),
            mock.call(
                "rally_atomic_action_data_v1",
                {
                    "deployment_uuid": "dep_uuid",
                    "deployment_name": "dep_name",
                    "action_name": "fail_something",
                    "scenario_cfg": ["key1=value1"],
                    "contexts": ["users@openstack.tenants=2"],
                    "runner_name": "foo",
                    "runner_cfg": ["times=3"],
                    "started_at": "1970-01-01T00:00:03",
                    "finished_at": "1970-01-01T00:00:04",
                    "duration": 1,
                    "success": not known_fail,
                    "error": itr_data["error"] if known_fail else None,
                    "parent": None,
                    "workload_uuid": "wid"},
                doc_id="foo_bar_uuid_action_fail_something_0"),
            mock.call(
                "rally_atomic_action_data_v1",
                {
                    "deployment_uuid": "dep_uuid",
                    "deployment_name": "dep_name",
                    "action_name": "rm -rf",
                    "scenario_cfg": ["key1=value1"],
                    "contexts": ["users@openstack.tenants=2"],
                    "runner_name": "foo",
                    "runner_cfg": ["times=3"],
                    "started_at": "1970-01-01T00:00:03",
                    "finished_at": "1970-01-01T00:00:04",
                    "duration": 1,
                    "success": not known_fail,
                    "error": itr_data["error"] if known_fail else None,
                    "parent": "foo_bar_uuid_action_fail_something_0",
                    "workload_uuid": "wid"},
                doc_id="foo_bar_uuid_action_rm -rf_0")]

        if not known_fail:
            expected_calls.append(mock.call(
                "rally_atomic_action_data_v1",
                {
                    "deployment_uuid": "dep_uuid",
                    "deployment_name": "dep_name",
                    "action_name": "no-name-action",
                    "scenario_cfg": ["key1=value1"],
                    "contexts": ["users@openstack.tenants=2"],
                    "runner_name": "foo",
                    "runner_cfg": ["times=3"],
                    "started_at": "1970-01-01T00:00:04",
                    "finished_at": "1970-01-01T00:00:04",
                    "duration": 0,
                    "success": False,
                    "error": itr_data["error"],
                    "parent": None,
                    "workload_uuid": "wid"},
                doc_id="foo_bar_uuid_action_no-name-action_0"))

        self.assertEqual(expected_calls, mock__add_index.call_args_list)

    def test_generate_fails_on_doc_exists(self):
        destination = "http://example.com"
        client = self.es_cls.return_value
        client.check_document.side_effect = (False, True)

        tasks = get_tasks_results()
        second_task = copy.deepcopy(tasks[-1])
        second_task["subtasks"] = []
        tasks.append(second_task)

        exporter = elastic.ElasticSearchExporter(tasks, destination)

        e = self.assertRaises(exceptions.RallyException, exporter.generate)
        self.assertIn("Failed to push the task %s" % tasks[0]["uuid"],
                      e.format_message())

    def test__ensure_indices(self):
        es = mock.MagicMock()
        exporter = elastic.ElasticSearchExporter([], None)
        exporter._client = es

        # case #1: everything exists
        es.list_indices.return_value = [exporter.WORKLOAD_INDEX,
                                        exporter.TASK_INDEX,
                                        exporter.AA_INDEX]
        exporter._ensure_indices()

        self.assertFalse(es.create_index.called)
        es.list_indices.assert_called_once_with()

        # case #2: some indices exist
        es.list_indices.reset_mock()
        es.list_indices.return_value = [exporter.TASK_INDEX, exporter.AA_INDEX]

        exporter._ensure_indices()

        es.list_indices.assert_called_once_with()
        es.create_index.assert_called_once_with(
            exporter.WORKLOAD_INDEX, doc_type="data",
            properties=exporter.INDEX_SCHEMAS[exporter.WORKLOAD_INDEX]
        )

        # case #3: none of indices exists
        es.list_indices.reset_mock()
        es.create_index.reset_mock()
        es.list_indices.return_value = []

        exporter._ensure_indices()

        es.list_indices.assert_called_once_with()
        self.assertEqual(3, es.create_index.call_count)

    @ddt.data(True, False)
    def test_generate(self, remote):
        if remote:
            destination = "http://example.com"
            client = self.es_cls.return_value
            client.check_document.return_value = False
        else:
            destination = "/home/bar.txt"

        tasks = get_tasks_results()
        second_task = copy.deepcopy(tasks[-1])
        second_task["subtasks"] = []
        tasks.append(second_task)

        exporter = elastic.ElasticSearchExporter(tasks, destination)

        result = exporter.generate()

        if remote:
            self.assertEqual(
                [mock.call("rally_task_data_v1", second_task["uuid"]),
                 mock.call("rally_task_data_v1", second_task["uuid"])],
                client.check_document.call_args_list
            )
            client.push_documents.assert_called_once_with(exporter._report)
            client.list_indices.assert_called_once_with()
            self.assertEqual(3, client.create_index.call_count)
        else:
            self.assertEqual({"files", "open"}, set(result.keys()))
            self.assertEqual("file://%s" % destination, result["open"])
            self.assertEqual({destination}, set(result["files"].keys()))

            data = result["files"][destination].split("\n")
            # the should be always empty line in the end
            self.assertEqual("", data[-1])

        data = [json.loads(line) for line in exporter._report]
        self.assertIsInstance(data, list)
        expected = [
            {
                "index": {"_id": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
                          "_index": "rally_task_data_v1",
                          "_type": "data"}
            },
            {
                "title": "foo",
                "description": "bar",
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "status": "ok",
                "pass_sla": "yup",
                "task_uuid": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
                "tags": ["tag-1", "tag-2"]
            },
            {
                "index": {"_id": "4dcd88a5-164b-4431-8b44-3979868116dd",
                          "_index": "rally_workload_data_v1",
                          "_type": "data"}
            },
            {
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "task_uuid": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
                "subtask_uuid": "35166362-0b11-4e74-929d-6988377e2da2",
                "scenario_name": "CinderVolumes.list_volumes",
                "description": "List all volumes.",
                "scenario_cfg": ["key1=value1"],
                "contexts": ["users@openstack.tenants=2"],
                "runner_name": "constant",
                "runner_cfg": ["times=3", "type=constant"],
                "full_duration": 127.59103488922119,
                "load_duration": 97.82577991485596,
                "started_at": "2017-07-28T23:35:50",
                "pass_sla": False,
                "success_rate": 0.8,
                "sla_details": ["because i do not like you"]
            },
            {
                "index": {
                    "_id": "4dcd88a5-164b-4431-8b44-3979868116dd_iter_1_action"
                           "_cinder.list_volumes_0",
                    "_index": "rally_atomic_action_data_v1",
                    "_type": "data"}
            },
            {
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "action_name": "cinder.list_volumes",
                "started_at": "2017-07-28T23:35:50",
                "finished_at": "2017-07-28T23:36:01",
                "duration": 11.096485137939453,
                "contexts": ["users@openstack.tenants=2"],
                "error": None,
                "parent": None,
                "runner_name": "constant",
                "runner_cfg": ["times=3", "type=constant"],
                "scenario_cfg": ["key1=value1"],
                "success": True,
                "workload_uuid": "4dcd88a5-164b-4431-8b44-3979868116dd"
            },
            {
                "index": {
                    "_id": "4dcd88a5-164b-4431-8b44-3979868116dd_iter_1_action"
                           "_no-name-action_0",
                    "_index": "rally_atomic_action_data_v1",
                    "_type": "data"}
            },
            {
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "action_name": "no-name-action",
                "started_at": "2017-07-28T23:36:00",
                "finished_at": "2017-07-28T23:36:00",
                "duration": 0,
                "contexts": ["users@openstack.tenants=2"],
                "error": ["ERROR!"],
                "parent": None,
                "runner_name": "constant",
                "runner_cfg": ["times=3", "type=constant"],
                "scenario_cfg": ["key1=value1"],
                "success": False,
                "workload_uuid": "4dcd88a5-164b-4431-8b44-3979868116dd"
            },
            {
                "index": {
                    "_id": "4dcd88a5-164b-4431-8b44-3979868116dd_iter_2_action"
                           "_cinder.list_volumes_0",
                    "_index": "rally_atomic_action_data_v1",
                    "_type": "data"}
            },
            {
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "action_name": "cinder.list_volumes",
                "started_at": "2017-07-28T23:35:50",
                "finished_at": "2017-07-28T23:36:01",
                "duration": 11.096485137939453,
                "contexts": ["users@openstack.tenants=2"],
                "error": ["ERROR!"],
                "parent": None,
                "runner_name": "constant",
                "runner_cfg": ["times=3", "type=constant"],
                "scenario_cfg": ["key1=value1"],
                "success": False,
                "workload_uuid": "4dcd88a5-164b-4431-8b44-3979868116dd"
            },
            {
                "index": {"_id": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
                          "_index": "rally_task_data_v1",
                          "_type": "data"}
            },
            {
                "deployment_uuid": "deployment-uuu-iii-iii-ddd",
                "deployment_name": "env-name",
                "title": "foo",
                "description": "bar",
                "status": "ok",
                "pass_sla": "yup",
                "task_uuid": "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8",
                "tags": ["tag-1", "tag-2"]}
        ]

        for i, line in enumerate(expected):
            if i == len(data):
                self.fail("The next line is missed: %s" % line)
            self.assertEqual(line, data[i], "Line #%s is wrong." % (i + 1))
