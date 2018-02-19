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

"""fix invalid verification logs

Revision ID: 08e1515a576c
Revises: 54e844ebfbc3
Create Date: 2016-09-12 15:47:11.279610

"""

import json

from alembic import op
import sqlalchemy as sa

from rally import consts
from rally import exceptions


# revision identifiers, used by Alembic.
revision = "08e1515a576c"
down_revision = "54e844ebfbc3"
branch_labels = None
depends_on = None


task_helper = sa.Table(
    "tasks",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("status", sa.Enum(*list(consts.TaskStatus),
                                name="enum_tasks_status"),
              default=consts.TaskStatus.INIT, nullable=False),
    sa.Column("verification_log", sa.Text, default=""),
    sa.Column("tag", sa.String(64), default=""),
    sa.Column("deployment_uuid", sa.String(36), nullable=False)
)


def _make_trace(etype, emsg, raw_trace=None):
    trace = "Traceback (most recent call last):\n"
    if raw_trace is None:
        trace += "\n\t\t...n/a..\n\n"
    else:
        trace += "".join(json.loads(raw_trace))

    trace += "%s: %s" % (etype, emsg)
    return trace


def upgrade():
    connection = op.get_bind()
    for task in connection.execute(task_helper.select()):
        verification_log = task.verification_log

        if not verification_log:
            continue

        new_value = None

        verification_log = json.loads(verification_log)
        if isinstance(verification_log, list):
            new_value = {"etype": verification_log[0],
                         "msg": verification_log[1],
                         "trace": verification_log[2]}
            if new_value["trace"].startswith("["):
                # NOTE(andreykurilin): For several cases traceback was
                #   transmitted as list instead of string.
                new_value["trace"] = _make_trace(*verification_log)
        else:
            if verification_log.startswith("No such file"):
                new_value = {"etype": IOError.__name__,
                             "msg": verification_log}
                new_value["trace"] = _make_trace(new_value["etype"],
                                                 new_value["msg"])
            elif verification_log.startswith("Task config is invalid"):
                new_value = {"etype": exceptions.InvalidTaskException.__name__,
                             "msg": verification_log}
                new_value["trace"] = _make_trace(new_value["etype"],
                                                 new_value["msg"])
            elif verification_log.startswith("Failed to load task"):
                new_value = {"etype": "FailedToLoadTask",
                             "msg": verification_log}
                new_value["trace"] = _make_trace(new_value["etype"],
                                                 new_value["msg"])

        if new_value:
            connection.execute(task_helper.update().where(
                task_helper.c.id == task.id).values(
                verification_log=json.dumps(new_value)))


def downgrade():
    raise exceptions.DowngradeNotSupported()
