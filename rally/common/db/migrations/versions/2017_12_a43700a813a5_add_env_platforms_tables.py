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

"""Add Env & Platforms tables

Revision ID: a43700a813a5
Revises: dc46687661df
Create Date: 2017-12-27 13:37:10.144970

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions


# revision identifiers, used by Alembic.
revision = "a43700a813a5"
down_revision = "44169f4d455e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "envs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", sa.String(36), nullable=False),

        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, default=""),
        sa.Column("status", sa.String(36), nullable=False),

        sa.Column("extras", sa_types.MutableJSONEncodedDict, default={}),
        sa.Column("spec", sa_types.MutableJSONEncodedDict, default={}),

        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime)
    )

    op.create_index("env_uuid", "envs", ["uuid"], unique=True)
    op.create_index("env_name", "envs", ["name"], unique=True)
    op.create_index("env_status", "envs", ["status"])

    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", sa.String(36), nullable=False),
        sa.Column("env_uuid", sa.String(36), nullable=False),

        sa.Column("status", sa.String(36), nullable=False),

        sa.Column("plugin_name", sa.String(36), nullable=False),
        sa.Column("plugin_spec", sa_types.MutableJSONEncodedDict,
                  nullable=False),
        sa.Column("plugin_data", sa_types.MutableJSONEncodedDict,
                  default={}),

        sa.Column("platform_name", sa.String(36)),
        sa.Column("platform_data", sa_types.MutableJSONEncodedDict,
                  default={}),

        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),

    )

    op.create_index("platform_uuid", "platforms", ["uuid"], unique=True)
    op.create_index("platform_env_uuid", "platforms", ["env_uuid"])


def downgrade():
    raise exceptions.DowngradeNotSupported()
