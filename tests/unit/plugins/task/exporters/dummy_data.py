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


def get_tasks_results():
    task_id = "2fa4f5ff-7d23-4bb0-9b1f-8ee235f7f1c8"
    workload = {"uuid": "uuid",
                "name": "CinderVolumes.list_volumes",
                "description": "List all volumes.",
                "created_at": "2017-06-04T05:14:44",
                "updated_at": "2017-06-04T05:15:14",
                "task_uuid": task_id,
                "position": 0,
                "data": [
                    {
                        "duration": 0.2504892349243164,
                        "timestamp": 1584551892.7336202,
                        "idle_duration": 0.0,
                        "error": [],
                        "output": {
                            "additive": [],
                            "complete": []
                        },
                        "atomic_actions": [
                            {
                                "name": "foo",
                                "children": [
                                    {
                                        "name": "bar",
                                        "children": [],
                                        "started_at": 1584551892.733688,
                                        "finished_at": 1584551892.984079
                                    }
                                ],
                                "started_at": 1584551892.7336745,
                                "finished_at": 1584551892.9840994
                            }
                        ]
                    },
                    {
                        "duration": 0.25043749809265137,
                        "timestamp": 1584551892.7363858,
                        "idle_duration": 0.0,
                        "error": [],
                        "output": {
                            "additive": [],
                            "complete": []
                        },
                        "atomic_actions": [
                            {
                                "name": "foo",
                                "children": [
                                    {
                                        "name": "bar",
                                        "children": [],
                                        "started_at": 1584551892.7364488,
                                        "finished_at": 1584551892.9867969
                                    }
                                ],
                                "started_at": 1584551892.736435,
                                "finished_at": 1584551892.9868152
                            }
                        ]
                    }
                ],
                "full_duration": 29.969523191452026,
                "load_duration": 2.03029203414917,
                "hooks": [],
                "runner": {},
                "runner_type": "runner_type",
                "args": {},
                "contexts": {},
                "contexts_results": [],
                "min_duration": 0.0,
                "max_duration": 1.0,
                "start_time": 0,
                "statistics": {},
                "failed_iteration_count": 0,
                "total_iteration_count": 10,
                "sla": {},
                "sla_results": {"sla": []},
                "pass_sla": True
                }
    task = {
        "uuid": task_id,
        "title": "task",
        "description": "description",
        "status": "finished",
        "env_uuid": "env-uuid",
        "env_name": "env-name",
        "tags": [],
        "created_at": "2017-06-04T05:14:44",
        "updated_at": "2017-06-04T05:15:14",
        "pass_sla": True,
        "task_duration": 2.0,
        "subtasks": [
            {"uuid": "subtask_uuid",
             "title": "subtask",
             "description": "description",
             "status": "finished",
             "run_in_parallel": True,
             "created_at": "2017-06-04T05:14:44",
             "updated_at": "2017-06-04T05:15:14",
             "sla": {},
             "duration": 29.969523191452026,
             "task_uuid": task_id,
             "workloads": [workload]}
        ]}
    return [task]
