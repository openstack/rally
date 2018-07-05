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

"""move_deployment_to_env_2

Migration 7287df262dbc did not handle the case of an old deployment format
which led to failures. Migration `dc0fe6de6786` ports the old format the new
one and we can perform the migration to the env again.

Revision ID: bc908ac9a1fc
Revises: dc0fe6de6786
Create Date: 2018-02-22 21:37:21.258560

"""

import copy
import datetime as dt
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection

from rally.common.db import sa_types
from rally import exceptions

# revision identifiers, used by Alembic.
revision = "bc908ac9a1fc"
down_revision = "dc0fe6de6786"
branch_labels = None
depends_on = None


STATUS_MAP = {
    "deploy->init": "INITIALIZING",
    "deploy->started": "INITIALIZING",
    "deploy->finished": "READY",
    "deploy->failed": "FAILED TO CREATE",
    "deploy->inconsistent": "FAILED TO CREATE",
    "deploy->subdeploy": "INITIALIZING",
    "cleanup->started": "CLEANING",
    "cleanup->failed": "READY",
    "cleanup->finished": "READY"
}


deployments_helper = sa.Table(
    "deployments",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("name", sa.String(255)),
    sa.Column("config", sa_types.MutableJSONEncodedDict()),
    sa.Column("credentials", sa_types.MutableJSONEncodedDict()),
    sa.Column("enum_deployments_status", sa.Enum(*STATUS_MAP.keys())),
    sa.Column("created_at", sa.DateTime),
)

envs_helper = sa.Table(
    "envs",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),

    sa.Column("name", sa.String(255)),
    sa.Column("description", sa.Text),
    sa.Column("status", sa.String(36)),

    sa.Column("extras", sa_types.MutableJSONEncodedDict),
    sa.Column("spec", sa_types.MutableJSONEncodedDict),

    sa.Column("created_at", sa.DateTime),
    sa.Column("updated_at", sa.DateTime)
)

platforms_helper = sa.Table(
    "platforms",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("env_uuid", sa.String(36)),

    sa.Column("status", sa.String(36)),

    sa.Column("plugin_name", sa.String(36)),
    sa.Column("plugin_spec", sa_types.MutableJSONEncodedDict),
    sa.Column("plugin_data", sa_types.MutableJSONEncodedDict),

    sa.Column("platform_name", sa.String(36)),
    sa.Column("platform_data", sa_types.MutableJSONEncodedDict),

    sa.Column("created_at", sa.DateTime),
    sa.Column("updated_at", sa.DateTime)
)

tasks_helper = sa.Table(
    "tasks",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),

    sa.Column("env_uuid", sa.String(36)),
    sa.Column("deployment_uuid", sa.String(36))
)

verifications_helper = sa.Table(
    "verifications",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),

    sa.Column("env_uuid", sa.String(36)),
    sa.Column("deployment_uuid", sa.String(36))
)


def upgrade():
    connection = op.get_bind()
    inspector = reflection.Inspector.from_engine(connection)
    if "deployments" not in inspector.get_table_names():
        # 7287df262dbc did not fail. nothing to do
        return

    envs = [env["uuid"] for env in connection.execute(envs_helper.select())]

    for deployment in connection.execute(deployments_helper.select()):
        if deployment["uuid"] in envs:
            # this deployment had been migrated by 7287df262dbc. Nothing to do
            continue
        status = "FAILED TO CREATE"
        spec = deployment.config
        extras = {}
        platform_data = None
        if isinstance(spec, dict) and (
                # existing cloud is only one deployment engine which we
                #   continue supporting
                spec.get("type", "") == "ExistingCloud"
                # We know only about one credential type and it doesn't require
                #   writing additional plugins at the moment.
                and (set(spec["creds"]) == {"openstack"}
                     or not spec["creds"])):

            status = STATUS_MAP[deployment.enum_deployments_status]
            extras = deployment.config.get("extra", {})
            if "openstack" in spec["creds"]:
                spec = {"existing@openstack": spec["creds"]["openstack"]}
                creds = copy.deepcopy(spec["existing@openstack"])

                platform_data = {
                    "admin": creds.pop("admin", {}),
                    "users": creds.pop("users", [])
                }
                platform_data["admin"].update(creds)
                for user in platform_data["users"]:
                    user.update(creds)
            else:
                # empty deployment
                spec = {}

        connection.execute(
            envs_helper.insert(),
            [{
                "uuid": deployment.uuid,
                "name": deployment.name,
                "description": "",
                "status": status,
                "spec": spec,
                "extras": extras,
                "created_at": deployment.created_at,
                "updated_at": dt.datetime.utcnow()
            }]
        )
        if platform_data:
            connection.execute(
                platforms_helper.insert(),
                [{
                    "uuid": str(uuid.uuid4()),
                    "env_uuid": deployment.uuid,
                    "status": "READY",
                    "plugin_name": "existing@openstack",
                    "plugin_spec": spec["existing@openstack"],
                    "plugin_data": {},
                    "platform_name": "openstack",
                    "platform_data": platform_data,
                    "created_at": dt.datetime.utcnow(),
                    "updated_at": dt.datetime.utcnow()
                }]
            )

    op.add_column(
        "verifications",
        sa.Column("env_uuid", sa.String(36))
    )
    op.add_column(
        "tasks",
        sa.Column("env_uuid", sa.String(36))
    )

    conn = op.get_bind()

    conn.execute(
        tasks_helper.update().values(
            env_uuid=tasks_helper.c.deployment_uuid)
    )
    conn.execute(
        verifications_helper.update().values(
            env_uuid=verifications_helper.c.deployment_uuid)
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("env_uuid", nullable=False)
        batch_op.drop_index("task_deployment")
        batch_op.drop_column("deployment_uuid")

    with op.batch_alter_table("verifications") as batch_op:
        batch_op.alter_column("env_uuid", nullable=False)
        batch_op.drop_column("deployment_uuid")

    op.drop_index("resource_deployment_uuid", "resources")
    op.drop_index("resource_provider_name", "resources")
    op.drop_index("resource_type", "resources")
    op.drop_index("resource_provider_name_and_type", "resources")
    op.drop_table("resources")

    op.drop_index("deployment_uuid", "deployments")
    op.drop_index("deployment_parent_uuid", "deployments")
    op.drop_table("deployments")


def downgrade():
    raise exceptions.DowngradeNotSupported()
