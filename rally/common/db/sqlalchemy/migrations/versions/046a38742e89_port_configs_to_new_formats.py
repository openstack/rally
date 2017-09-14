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

"""port-configs-to-new-formats

Revision ID: 046a38742e89
Revises: fab4f4f31f8a
Create Date: 2017-09-14 15:58:28.950132

"""

from alembic import op
import json
import sqlalchemy as sa

from rally import exceptions

# revision identifiers, used by Alembic.
revision = "046a38742e89"
down_revision = "fab4f4f31f8a"
branch_labels = None
depends_on = None


workload_helper = sa.Table(
    "workloads",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),

    sa.Column("runner", sa.Text),
    sa.Column("hooks", sa.Text)
)


def upgrade():
    connection = op.get_bind()

    for workload in connection.execute(workload_helper.select()):
        runner = json.loads(workload["runner"])
        runner.pop("type")
        values = {"runner": json.dumps(runner)}
        hooks = workload["hooks"]
        if hooks:
            values["hooks"] = []
            for hook in json.loads(hooks):
                hook_cfg = hook["config"]
                trigger_cfg = hook_cfg["trigger"]
                hook["config"] = {
                    "description": hook_cfg.get("description"),
                    "action": (hook_cfg["name"], hook_cfg["args"]),
                    "trigger": (trigger_cfg["name"], trigger_cfg["args"])}
                values["hooks"].append(hook)
            values["hooks"] = json.dumps(values["hooks"])
        connection.execute(workload_helper.update().where(
            workload_helper.c.uuid == workload.uuid).values(
            **values))


def downgrade():
    raise exceptions.DowngradeNotSupported()
