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

"""refactor_credentials

Revision ID: 92aaaa2a6bb3
Revises: 4ef544102ba7
Create Date: 2017-02-01 12:52:43.499663

"""
from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "92aaaa2a6bb3"
down_revision = "4ef544102ba7"
branch_labels = None
depends_on = None


deployments_helper = sa.Table(
    "deployments",
    sa.MetaData(),
    sa.Column("name", sa.String(255), unique=True),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("credentials", sa.PickleType, nullable=True),
    sa.Column("new_credentials", sa_types.MutableJSONEncodedDict,
              default={}, nullable=False)
)


def upgrade():
    with op.batch_alter_table("deployments") as batch_op:
        batch_op.add_column(
            sa.Column("new_credentials", sa_types.MutableJSONEncodedDict,
                      default={}))

    connection = op.get_bind()
    for deployment in connection.execute(deployments_helper.select()):
        creds = {}
        for cred_type, cred_obj in deployment.credentials:
            creds.setdefault(cred_type, [])
            creds[cred_type].append(cred_obj)

        connection.execute(
            deployments_helper.update().where(
                deployments_helper.c.id == deployment.id).values(
                new_credentials=creds))

    with op.batch_alter_table("deployments") as batch_op:
        batch_op.drop_column("credentials")
        batch_op.alter_column("new_credentials", new_column_name="credentials",
                              existing_type=sa_types.MutableJSONEncodedDict,
                              nullable=False)


def downgrade():
    raise exceptions.DowngradeNotSupported()
