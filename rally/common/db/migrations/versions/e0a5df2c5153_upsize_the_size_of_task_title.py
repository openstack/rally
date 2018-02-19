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

"""Upsize the size of task.title and subtask.title from 64 to 128

Revision ID: e0a5df2c5153
Revises: 7948b83229f6
Create Date: 2017-09-05 16:34:47.434748

"""
from alembic import op
import sqlalchemy as sa

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "e0a5df2c5153"
down_revision = "7948b83229f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "title", type_=sa.String(128), existing_type=sa.String(64))

    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.alter_column(
            "title", type_=sa.String(128), existing_type=sa.String(64))


def downgrade():
    raise exceptions.DowngradeNotSupported()
