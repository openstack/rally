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

"""Update_deployment_configs

Previously we had bad deployment config validation

Revision ID: 54e844ebfbc3
Revises: 3177d36ea270
Create Date: 2016-07-24 14:53:39.323105

"""

from alembic import op  # noqa
import sqlalchemy as sa  # noqa

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "54e844ebfbc3"
down_revision = "3177d36ea270"
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


def _check_user_entry(user):
    """Fixes wrong format of users."""
    if "tenant_name" in user:
        keys = set(user.keys())
        if keys == {"username", "password", "tenant_name",
                    "project_domain_name", "user_domain_name"}:
            if (user["user_domain_name"] == "" and
                    user["project_domain_name"] == ""):
                # it is credentials of keystone v2 and they were created
                # --fromenv
                del user["user_domain_name"]
                del user["project_domain_name"]
                return True
            else:
                # it looks like keystone v3 credentials
                user["project_name"] = user.pop("tenant_name")
                return True


def upgrade():
    connection = op.get_bind()
    for deployment in connection.execute(deployments_helper.select()):
        conf = deployment.config
        if conf["type"] != "ExistingCloud":
            continue

        should_update = False

        if _check_user_entry(conf["admin"]):
            should_update = True
        if "users" in conf:
            for user in conf["users"]:
                if _check_user_entry(user):
                    should_update = True

        if conf.get("endpoint_type") == "public":
            del conf["endpoint_type"]
            should_update = True

        if should_update:
            connection.execute(
                deployments_helper.update().where(
                    deployments_helper.c.id == deployment.id).values(
                    config=conf))


def downgrade():
    raise exceptions.DowngradeNotSupported()
