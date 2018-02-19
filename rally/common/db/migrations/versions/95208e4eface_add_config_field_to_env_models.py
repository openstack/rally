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

"""Add config field to env models

Revision ID: 95208e4eface
Revises: 7287df262dbc
Create Date: 2018-02-04 13:48:35.779255

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions


# revision identifiers, used by Alembic.
revision = "95208e4eface"
down_revision = "7287df262dbc"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("envs") as batch_op:
        batch_op.add_column(
            sa.Column("config", sa_types.MutableJSONEncodedDict))


def downgrade():
    raise exceptions.DowngradeNotSupported()
