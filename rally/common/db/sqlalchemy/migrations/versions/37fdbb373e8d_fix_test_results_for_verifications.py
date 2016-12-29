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

"""Fix test results for verifications

Revision ID: 37fdbb373e8d
Revises: 484cd9413e66
Create Date: 2016-12-29 19:54:23.804525

"""

# revision identifiers, used by Alembic.
revision = "37fdbb373e8d"
down_revision = "484cd9413e66"
branch_labels = None
depends_on = None


from alembic import op
import sqlalchemy as sa

from rally.common.db.sqlalchemy import types as sa_types
from rally import exceptions


verifications_helper = sa.Table(
    "verifications",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("tests", sa_types.MutableJSONEncodedDict, default={})
)


def upgrade():
    connection = op.get_bind()
    for v in connection.execute(verifications_helper.select()):
        tests = v.tests
        for test in tests.values():
            duration = test.pop("time")
            test["duration"] = duration

        connection.execute(
            verifications_helper.update().where(
                verifications_helper.c.id == v.id).values(tests=tests))


def downgrade():
    raise exceptions.DowngradeNotSupported()
