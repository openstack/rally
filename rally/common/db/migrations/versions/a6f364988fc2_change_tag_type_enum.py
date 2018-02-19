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

"""Change tag type enum

Revision ID: a6f364988fc2
Revises: 37fdbb373e8d
Create Date: 2017-01-17 18:47:10.700459

"""
from alembic import op
import sqlalchemy as sa

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "a6f364988fc2"
down_revision = "37fdbb373e8d"
branch_labels = None
depends_on = None


TAG_TYPES = ["task", "subtask"]

tag_helper = sa.Table(
    "tags",
    sa.MetaData(),
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("type", sa.Enum(*TAG_TYPES, name="enum_tag_types"),
              nullable=False),
    sa.Column("new_type", sa.String(36), nullable=False)
)


def upgrade():
    with op.batch_alter_table("tags") as batch_op:
        batch_op.add_column(
            sa.Column("new_type", sa.String(36)))

    op.execute(tag_helper.update().values(new_type=tag_helper.c.type))

    op.drop_index("d_type_tag", "tags")

    with op.batch_alter_table("tags") as batch_op:
        batch_op.drop_column("type")
        batch_op.alter_column("new_type", new_column_name="type",
                              existing_type=sa.String(36), nullable=False)

    op.create_index("d_type_tag", "tags", ["uuid", "type", "tag"], unique=True)


def downgrade():
    raise exceptions.DowngradeNotSupported()
