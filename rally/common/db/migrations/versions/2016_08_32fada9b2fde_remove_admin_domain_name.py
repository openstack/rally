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

"""Remove admin domain name

Revision ID: 32fada9b2fde
Revises: 5b983f0c9b9a
Create Date: 2016-08-29 08:32:30.818019

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "32fada9b2fde"
down_revision = "6ad4f426f005"
branch_labels = None
depends_on = None


deployments_helper = sa.Table(
    "deployments",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "config",
        sa_types.MutableJSONEncodedDict,
        default={},
        nullable=False,
    )
)


def upgrade():
    connection = op.get_bind()
    for deployment in connection.execute(deployments_helper.select()):
        conf = deployment.config
        if conf["type"] != "ExistingCloud":
            continue

        should_update = False

        if "admin_domain_name" in conf["admin"]:
            del conf["admin"]["admin_domain_name"]
            should_update = True
        if "users" in conf:
            for user in conf["users"]:
                if "admin_domain_name" in user:
                    del user["admin_domain_name"]
                    should_update = True

        if should_update:
            connection.execute(
                deployments_helper.update().where(
                    deployments_helper.c.id == deployment.id).values(
                    config=conf))


def downgrade():
    raise exceptions.DowngradeNotSupported()
