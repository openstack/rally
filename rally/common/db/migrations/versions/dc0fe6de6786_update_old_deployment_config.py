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

"""update_old_deployment_config

Revision ID: dc0fe6de6786
Revises: 95208e4eface
Create Date: 2018-02-22 21:02:41.822469

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "dc0fe6de6786"
down_revision = "95208e4eface"
branch_labels = None
depends_on = None

deployments_helper = sa.Table(
    "deployments",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("config", sa_types.MutableJSONEncodedDict()),
)


def upgrade():
    connection = op.get_bind()
    inspector = reflection.Inspector.from_engine(connection)
    if "deployments" not in inspector.get_table_names():
        # 7287df262dbc did not fail. nothing to do
        return

    for deployment in connection.execute(deployments_helper.select()):
        config = deployment.config
        if isinstance(config, dict) and (
                config.get("type", "") == "ExistingCloud"
                and "creds" not in config):
            extra = config.pop("extra", None)
            dtype = config.pop("type")
            config = {
                "type": dtype,
                "creds": {"openstack": config}
            }
            if extra is not None:
                config["extra"] = extra
            connection.execute(
                deployments_helper.update().where(
                    deployments_helper.c.id == deployment.id).values(
                    config=config))


def downgrade():
    raise exceptions.DowngradeNotSupported()
