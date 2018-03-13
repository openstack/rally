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

"""Change task status enum

Revision ID: 4ef544102ba7
Revises: 3177d36ea270
Create Date: 2016-04-22 21:28:50.745316

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import consts
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "4ef544102ba7"
down_revision = "f33f4610dcda"
branch_labels = None
depends_on = None


OLD_STATUS = [
    "aborted", "aborting", "cleaning up", "failed", "finished",
    "init", "paused", "running", "setting up", "soft_aborting", "verifying"
]
OLD_ENUM = sa.Enum(*OLD_STATUS, name="enum_tasks_status")

WITHOUT_CHANGES = (
    "init", "running", "aborted", "aborting", "soft_aborting", "paused",
    "finished"
)

OLD_TO_NEW = [
    ("verifying", "validating",),
    ("failed", "crashed",)
]


task = sa.Table(
    "tasks",
    sa.MetaData(),
    sa.Column("created_at", sa.DateTime(), nullable=True),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("uuid", sa.String(length=36), nullable=False),
    sa.Column("deployment_uuid", sa.String(length=36), nullable=False),
    sa.Column("title", sa.String(length=64), default=""),
    sa.Column("description", sa.Text(), default=""),
    sa.Column("input_task", sa.Text(), default=""),
    sa.Column("validation_duration", sa.Float()),
    sa.Column("task_duration", sa.Float()),
    sa.Column("pass_sla", sa.Boolean()),
    sa.Column("status", OLD_ENUM, nullable=False),
    sa.Column("new_status", sa.String(36),
              default=consts.TaskStatus.INIT),
    sa.Column(
        "validation_result",
        sa_types.MutableJSONEncodedDict(),
        default={},
        nullable=False
    )
)

subtask = sa.Table(
    "subtasks",
    sa.MetaData(),
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
    sa.Column("status", OLD_ENUM, nullable=False),
    sa.Column("new_status", sa.String(36),
              default=consts.SubtaskStatus.RUNNING),
    sa.ForeignKeyConstraint(["task_uuid"], ["tasks.uuid"], ),
    sa.PrimaryKeyConstraint("id")
)


def upgrade():
    # Workaround for Alemic bug #89
    # https://bitbucket.org/zzzeek/alembic/issue/89

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("new_status", sa.String(36),
                                      default=consts.TaskStatus.INIT))
    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.add_column(sa.Column("new_status", sa.String(36),
                                      default=consts.SubtaskStatus.RUNNING))

    op.execute(
        task.update()
            .where(task.c.status.in_(WITHOUT_CHANGES))
            .values({"new_status": task.c.status}))

    for old, new in OLD_TO_NEW:
        op.execute(
            task.update()
                .where(task.c.status == op.inline_literal(old))
                .values({"new_status": new}))

    # NOTE(rvasilets): Assume that set_failed was used only in causes of
    # validation failed
    op.execute(
        task.update().where(
            (task.c.status == op.inline_literal("failed")) &
            (task.c.validation_result == {})).values(
            {"new_status": "crashed", "validation_result": {}}))
    op.execute(
        task.update().where(
            (task.c.status == op.inline_literal("failed")) &
            (task.c.validation_result != {})).values(
            {"new_status": "validation_failed",
             "validation_result": task.c.validation_result}))

    op.drop_index("task_status", "tasks")
    op.drop_index("subtask_status", "subtasks")

    # NOTE(boris-42): Statuses "setting up", "cleaning up" were not used
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("status")
        batch_op.alter_column("new_status", new_column_name="status",
                              existing_type=sa.String(36))
    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.drop_column("status")
        batch_op.alter_column("new_status", new_column_name="status",
                              existing_type=sa.String(36))

    op.create_index("task_status", "tasks", ["status"])
    op.create_index("subtask_status", "subtasks", ["status"])


def downgrade():
    raise exceptions.DowngradeNotSupported()
