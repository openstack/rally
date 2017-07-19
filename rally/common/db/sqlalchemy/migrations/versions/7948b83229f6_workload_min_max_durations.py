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

"""workload-min-max-durations

Revision ID: 7948b83229f6
Revises: c517b0011857
Create Date: 2017-07-22 08:45:25.726422

"""

from alembic import op
import sqlalchemy as sa


from rally import exceptions

# revision identifiers, used by Alembic.
revision = "7948b83229f6"
down_revision = "c517b0011857"
branch_labels = None
depends_on = None


workload_helper = sa.Table(
    "workloads",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("min_duration", sa.Float),
    sa.Column("max_duration", sa.Float)
)

workload_data_helper = sa.Table(
    "workloaddata",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("workload_uuid", sa.String(length=36), nullable=False)
)


def upgrade():
    connection = op.get_bind()
    for workload in connection.execute(workload_helper.select()):
        # NOTE(andreykurilin): the cases of "wrong" values for min_duration
        #   and max_duration are equal. Let's check everything for
        #   min_duration and apply for both.
        should_update = False
        if workload.min_duration == -1:
            # it is left from the migration to Task Format V2
            should_update = True
        elif workload.min_duration == 0:
            # should check existence of workload data to ensure where 0 is a
            # real min_duration or it is just previous default value
            r = (connection.execute(workload_data_helper.select().where(
                 workload_data_helper.c.workload_uuid == workload.uuid))
                 .first())
            if not r:
                should_update = True

        if should_update:
            connection.execute(workload_helper.update().where(
                workload_helper.c.uuid == workload.uuid).values(
                min_duration=None, max_duration=None))


def downgrade():
    raise exceptions.DowngradeNotSupported()
