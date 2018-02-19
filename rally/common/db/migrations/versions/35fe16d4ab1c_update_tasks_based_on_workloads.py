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

"""update-tasks-based-on-workloads

Update "pass_sla" and "duration" fields of tasks and subtasks based on
workloads.

Revision ID: 35fe16d4ab1c
Revises: 92aaaa2a6bb3
Create Date: 2017-06-07 19:50:03.572493

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "35fe16d4ab1c"
down_revision = "92aaaa2a6bb3"
branch_labels = None
depends_on = None


task_helper = sa.Table(
    "tasks",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("task_duration", sa.Float()),
    sa.Column("pass_sla", sa.Boolean())
)

subtask_helper = sa.Table(
    "subtasks",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("duration", sa.Float()),
    sa.Column("pass_sla", sa.Boolean())
)

workload_helper = sa.Table(
    "workloads",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("task_uuid", sa.String(length=36), nullable=False),
    sa.Column("subtask_uuid", sa.String(length=36), nullable=False),
    sa.Column("load_duration", sa.Float()),
    sa.Column("pass_sla", sa.Boolean()),
)


def upgrade():
    tasks = {}
    subtasks = {}

    with op.batch_alter_table("workloads") as batch_op:
        # change type of column
        batch_op.drop_column("start_time")
        batch_op.add_column(sa.Column("start_time", sa_types.TimeStamp))

    connection = op.get_bind()

    for w in connection.execute(workload_helper.select()):
        tasks.setdefault(w.task_uuid, {"task_duration": 0, "pass_sla": True})
        subtasks.setdefault(w.subtask_uuid, {"duration": 0, "pass_sla": True})
        tasks[w.task_uuid]["task_duration"] += w.load_duration
        subtasks[w.subtask_uuid]["duration"] += w.load_duration

        if not w.pass_sla:
            tasks[w.task_uuid]["pass_sla"] = False
            subtasks[w.subtask_uuid]["pass_sla"] = False

    for subtask in connection.execute(subtask_helper.select()):
        values = subtasks.get(subtask.uuid, {"duration": 0.0,
                                             "pass_sla": True})
        connection.execute(subtask_helper.update().where(
            subtask_helper.c.id == subtask.id).values(**values))

    for task in connection.execute(task_helper.select()):
        values = tasks.get(task.uuid, {"task_duration": 0.0,
                                       "pass_sla": True})
        connection.execute(task_helper.update().where(
            task_helper.c.id == task.id).values(**values))


def downgrade():
    raise exceptions.DowngradeNotSupported()
