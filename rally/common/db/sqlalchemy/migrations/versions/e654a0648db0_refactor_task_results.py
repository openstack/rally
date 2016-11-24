# Copyright (c) 2016 Mirantis Inc.
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

"""Refactor task results

Revision ID: e654a0648db0
Revises: 3177d36ea270
Create Date: 2016-04-01 14:36:56.373349

"""

# revision identifiers, used by Alembic.
revision = "e654a0648db0"
down_revision = "32fada9b2fde"
branch_labels = None
depends_on = None

import datetime as dt
import json
import uuid

from alembic import op
import sqlalchemy as sa

from rally.common.db.sqlalchemy import types as sa_types
from rally import exceptions

taskhelper = sa.Table(
    "tasks",
    sa.MetaData(),
    sa.Column("created_at", sa.DateTime(), nullable=True),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("uuid", sa.String(length=36), nullable=False),
    sa.Column("status", sa.Enum(
        "aborted", "aborting", "cleaning up", "failed", "finished",
        "init", "paused", "running", "setting up", "soft_aborting",
        "verifying", name="enum_tasks_status"), nullable=False),
    sa.Column("verification_log", sa.Text(), nullable=True),
    sa.Column("tag", sa.String(length=64), nullable=True),
    sa.Column("deployment_uuid", sa.String(length=36), nullable=False),
    sa.Column("title", sa.String(length=64), default=""),
    sa.Column("description", sa.Text(), default=""),
    sa.Column("input_task", sa.Text(), default=""),
    sa.Column("validation_duration", sa.Float()),
    sa.Column("task_duration", sa.Float()),
    sa.Column("pass_sla", sa.Boolean()),
    sa.Column(
        "validation_result",
        sa_types.MutableJSONEncodedDict(),
        default={},
        nullable=False
    )
)

task_result_helper = sa.Table(
    "task_results",
    sa.MetaData(),
    sa.Column("created_at", sa.DateTime()),
    sa.Column("updated_at", sa.DateTime()),
    sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
    sa.Column(
        "key",
        sa_types.MutableJSONEncodedDict(),
        nullable=False),
    sa.Column(
        "data",
        sa_types.MutableJSONEncodedDict(),
        nullable=False),
    sa.Column("task_uuid", sa.String(length=36), nullable=True)
)

taghelper = sa.Table(
    "tags",
    sa.MetaData(),
    sa.Column("created_at", sa.DateTime()),
    sa.Column("updated_at", sa.DateTime()),
    sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
    sa.Column("uuid", sa.String(length=36), nullable=False),
    sa.Column("tag", sa.String(length=255), nullable=False),

    sa.Column(
        "type",
        sa.Enum(
            "task", "subtask",
            name="enum_tag_types"),
        nullable=False)
)


def upgrade():
    conn = op.get_bind()

    subtask_table = op.create_table(
        "subtasks",
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("task_uuid", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=64), default=""),
        sa.Column("description", sa.Text(), default=""),
        sa.Column(
            "context",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "sla",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column("duration", sa.Float()),

        sa.Column(
            "run_in_parallel",
            sa.Boolean(),
            default=False,
            nullable=False),

        sa.Column("pass_sla", sa.Boolean()),

        sa.Column(
            "status",
            sa.Enum(
                "finished", "running", "crashed",
                name="enum_subtasks_status"),
            nullable=False),

        sa.ForeignKeyConstraint(["task_uuid"], ["tasks.uuid"], ),
        sa.PrimaryKeyConstraint("id")

    )

    op.create_index("subtask_uuid", "subtasks", ["uuid"], unique=True)
    op.create_index("subtask_status", "subtasks", ["status"], unique=False)

    workload_table = op.create_table(
        "workloads",
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("task_uuid", sa.String(length=36), nullable=False),
        sa.Column("subtask_uuid", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("position", sa.Integer(), default=0, nullable=False),

        sa.Column(
            "runner_type",
            sa.String(length=64),
            nullable=False),

        sa.Column(
            "runner",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "args",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "context",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "hooks",
            sa_types.MutableJSONEncodedList(),
            default=[],
            nullable=False),

        sa.Column(
            "sla",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "sla_results",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column(
            "context_execution",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.Column("load_duration", sa.Float(), default=0),
        sa.Column("full_duration", sa.Float(), default=0),
        sa.Column("min_duration", sa.Float(), default=0),
        sa.Column("max_duration", sa.Float(), default=0),
        sa.Column("total_iteration_count", sa.Integer(), default=0),
        sa.Column("failed_iteration_count", sa.Integer(), default=0),

        sa.Column("pass_sla", sa.Boolean()),

        sa.Column(
            "statistics",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),


        sa.Column("start_time", sa.DateTime()),
        sa.Column("_profiling_data", sa.Text(), default=""),

        sa.ForeignKeyConstraint(["task_uuid"], ["tasks.uuid"], ),
        sa.ForeignKeyConstraint(["subtask_uuid"], ["subtasks.uuid"], ),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("workload_uuid", "workloads", ["uuid"], unique=True)

    workloaddata_table = op.create_table(
        "workloaddata",
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("task_uuid", sa.String(length=36), nullable=False),
        sa.Column("workload_uuid", sa.String(length=36), nullable=False),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("iteration_count", sa.Integer(), nullable=False),
        sa.Column("failed_iteration_count", sa.Integer(), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),

        sa.Column(
            "compressed_chunk_size",
            sa.Integer(),
            nullable=False),

        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        # sa.Column("chunk_data", sa.Text(), nullable=False),
        sa.Column(
            "chunk_data",
            sa_types.MutableJSONEncodedDict(),
            default={},
            nullable=False),

        sa.ForeignKeyConstraint(["task_uuid"], ["tasks.uuid"], ),
        sa.ForeignKeyConstraint(["workload_uuid"], ["workloads.uuid"], ),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index(
        "workload_data_uuid", "workloaddata", ["uuid"], unique=True)

    tag_table = op.create_table(
        "tags",
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("tag", sa.String(length=255), nullable=False),

        sa.Column(
            "type",
            sa.Enum(
                "task", "subtask",
                name="enum_tag_types"),
            nullable=False),

        sa.PrimaryKeyConstraint("id")
    )

    op.create_index(
        "d_type_tag", "tags", ["uuid", "type", "tag"], unique=True)

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(
            sa.Column("title", sa.String(length=64), default="")
        )

        batch_op.add_column(
            sa.Column("description", sa.Text(), default="")
        )

        batch_op.add_column(
            sa.Column("input_task", sa.Text(), default="")
        )

        batch_op.add_column(
            sa.Column("validation_duration", sa.Float())
        )

        batch_op.add_column(
            sa.Column("task_duration", sa.Float())
        )

        batch_op.add_column(
            sa.Column("pass_sla", sa.Boolean())
        )

        batch_op.add_column(
            sa.Column(
                "validation_result",
                sa_types.MutableJSONEncodedDict(),
                default={})
        )

    for task in conn.execute(taskhelper.select()):
        if task.tag:
            conn.execute(
                tag_table.insert(),
                [{
                    "uuid": task.uuid,
                    "type": "task",
                    "tag": task.tag,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at
                }]
            )

        task_results = conn.execute(
            task_result_helper.select().
            where(task_result_helper.c.task_uuid == task.uuid)
        )

        pass_sla = True
        task_duration = 0

        for task_result in task_results:
            raw_data = task_result.data.get("raw", [])
            iter_count = len(raw_data)

            failed_iter_count = 0
            max_duration = 0
            min_duration = -1

            for d in raw_data:
                if d.get("error"):
                    failed_iter_count += 1

                duration = d.get("duration", 0)

                if duration > max_duration:
                    max_duration = duration

                if min_duration < 0 or min_duration > duration:
                    min_duration = duration

            sla = task_result.data.get("sla", [])
            success = all([s.get("success") for s in sla])

            if not success:
                pass_sla = False

            task_duration += task_result.data.get("full_duration", 0)

            delta = dt.timedelta(
                seconds=task_result.data.get("full_duration", 0))
            start = task_result.created_at - delta

            subtask_uuid = str(uuid.uuid4())

            conn.execute(
                subtask_table.insert(),
                [{
                    "uuid": subtask_uuid,
                    "task_uuid": task.uuid,
                    "created_at": task_result.created_at,
                    "updated_at": task_result.updated_at,
                    # NOTE(ikhudoshyn) We don't have info on subtask status
                    "status": "finished",
                    "duration": task_result.data.get("full_duration", 0),
                    "pass_sla": success
                }]
            )

            workload_uuid = str(uuid.uuid4())

            conn.execute(
                workload_table.insert(),
                [{
                    "created_at": task_result.created_at,
                    "updated_at": task_result.updated_at,
                    "uuid": workload_uuid,
                    "task_uuid": task.uuid,
                    "subtask_uuid": subtask_uuid,
                    "name": task_result.key["name"],
                    "position": task_result.key["pos"],
                    "runner_type": task_result.key["kw"]["runner"]["type"],
                    "runner": task_result.key["kw"]["runner"],
                    "context": task_result.key["kw"].get("context", {}),
                    "sla": task_result.key["kw"].get("sla", {}),
                    "args": task_result.key["kw"].get("args", {}),
                    "sla_results": {"sla": sla},
                    "context_execution": {},
                    "load_duration": task_result.data.get("load_duration", 0),
                    "full_duration": task_result.data.get("full_duration", 0),
                    "min_duration": min_duration,
                    "max_duration": max_duration,
                    "total_iteration_count": iter_count,
                    "failed_iteration_count": failed_iter_count,
                    "pass_sla": success,
                    "statistics": {},
                    "start_time": start,
                }]
            )

            conn.execute(
                workloaddata_table.insert(),
                [{
                    "uuid": str(uuid.uuid4()),
                    "task_uuid": task.uuid,
                    "workload_uuid": workload_uuid,
                    "chunk_order": 0,
                    "iteration_count": iter_count,
                    "failed_iteration_count": failed_iter_count,
                    "chunk_data": {"raw": raw_data},
                    # TODO(ikhudoshyn)
                    "chunk_size": 0,
                    "compressed_chunk_size": 0,
                    "started_at": start,
                    "finished_at": task_result.created_at
                }]
            )

        task_verification_log = {}
        if task.verification_log:
            task_verification_log = json.loads(task.verification_log)

        conn.execute(
            taskhelper.update().where(taskhelper.c.uuid == task.uuid),
            {
                "pass_sla": pass_sla,
                "task_duration": task_duration,
                "validation_duration": 0,
                "validation_result": task_verification_log
            }
        )

    # TODO(ikhudoshyn) update workload's statistics

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("tag")
        batch_op.drop_column("verification_log")
        batch_op.alter_column(
            "validation_result",
            existing_type=sa_types.MutableJSONEncodedDict(),
            nullable=False)

    op.drop_table("task_results")


def downgrade():
    raise exceptions.DowngradeNotSupported()
