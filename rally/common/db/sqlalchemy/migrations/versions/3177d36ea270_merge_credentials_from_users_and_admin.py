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

"""Merge credentials from users and admin

Revision ID: 3177d36ea270
Revises: ca3626f62937
Create Date: 2016-03-01 16:01:38.747048

"""

# revision identifiers, used by Alembic.
revision = "3177d36ea270"
down_revision = "ca3626f62937"
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa

from rally import exceptions


deployments_helper = sa.Table(
    "deployments",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("admin", sa.types.PickleType, nullable=True),
    sa.Column("users", sa.types.PickleType, default=[], nullable=False),
    sa.Column("credentials", sa.types.PickleType, nullable=True),
)


def upgrade():
    with op.batch_alter_table("deployments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("credentials", sa.PickleType(), nullable=True))

    connection = op.get_bind()
    for deployment in connection.execute(deployments_helper.select()):
        creds = [
            ["openstack",
             {
                 "admin": deployment.admin,
                 "users": deployment.users
             }]
        ]
        connection.execute(
            deployments_helper.update().where(
                deployments_helper.c.id == deployment.id).values(
                credentials=creds))

    with op.batch_alter_table("deployments", schema=None) as batch_op:
        batch_op.alter_column("credentials",
                              existing_type=sa.PickleType,
                              existing_nullable=True,
                              nullable=False)
        batch_op.drop_column("admin")
        batch_op.drop_column("users")


def downgrade():
    raise exceptions.DowngradeNotSupported()
