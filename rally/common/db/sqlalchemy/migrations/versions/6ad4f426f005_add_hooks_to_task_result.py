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

"""add hooks to task result

Adds empty hooks list to existing task results

Revision ID: 6ad4f426f005
Revises: 08e1515a576c
Create Date: 2016-09-13 18:11:47.703023

"""

# revision identifiers, used by Alembic.
revision = "6ad4f426f005"
down_revision = "08e1515a576c"
branch_labels = None
depends_on = None

from alembic import op  # noqa
import sqlalchemy as sa  # noqa

from rally.common.db.sqlalchemy import types as sa_types
from rally import exceptions


task_results_helper = sa.Table(
    "task_results",
    sa.MetaData(),
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("data", sa_types.MutableJSONEncodedDict(), nullable=False),
)


def upgrade():
    connection = op.get_bind()
    for task_result in connection.execute(task_results_helper.select()):
        data = task_result.data
        data["hooks"] = []
        connection.execute(
            task_results_helper.update().where(
                task_results_helper.c.id == task_result.id).values(
                    data=data))


def downgrade():
    raise exceptions.DowngradeNotSupported()
