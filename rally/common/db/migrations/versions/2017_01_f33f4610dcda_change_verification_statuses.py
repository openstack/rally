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

"""Change verification statuses

Revision ID: f33f4610dcda
Revises: a6f364988fc2
Create Date: 2017-01-23 13:56:30.999593

"""

from alembic import op
import sqlalchemy as sa

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "f33f4610dcda"
down_revision = "a6f364988fc2"
branch_labels = None
depends_on = None


verifications_helper = sa.Table(
    "verifications",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("failures", sa.Integer, default=0),
    sa.Column("unexpected_success", sa.Integer, default=0),
    sa.Column("status", sa.String(36), nullable=False)
)


def upgrade():
    connection = op.get_bind()
    for v in connection.execute(verifications_helper.select()):
        new_status = v.status
        if v.status == "finished" and (
                v.failures != 0 or v.unexpected_success != 0):
            new_status = "failed"
        elif v.status == "failed":
            new_status = "crashed"
        else:
            pass

        if new_status != v.status:
            connection.execute(verifications_helper.update().where(
                verifications_helper.c.id == v.id).values(
                status=new_status))


def downgrade():
    raise exceptions.DowngradeNotSupported()
