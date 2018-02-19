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

"""Rename Namespace To Platform

Revision ID: 9a18c6fe265c
Revises: 046a38742e89
Create Date: 2017-10-12 17:28:17.636938

"""

from alembic import op

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "9a18c6fe265c"
down_revision = "046a38742e89"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("verifiers") as batch_op:
        batch_op.alter_column("namespace", new_column_name="platform")


def downgrade():
    raise exceptions.DowngradeNotSupported()
