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

"""fill_missed_workload_info_r3

Revision ID: 4394bdc32cfd
Revises: 9a18c6fe265c
Create Date: 2017-10-15 22:45:04.963524

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions
from rally.task.processing import charts


# revision identifiers, used by Alembic.
revision = "4394bdc32cfd"
down_revision = "9a18c6fe265c"
branch_labels = None
depends_on = None


workload_helper = sa.Table(
    "workloads",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("start_time", sa_types.TimeStamp),
    sa.Column("statistics", sa_types.MutableJSONEncodedDict, default={},
              nullable=False),
)

workload_data_helper = sa.Table(
    "workloaddata",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("workload_uuid", sa.String(length=36), nullable=False),
    sa.Column("chunk_data", sa_types.MutableJSONEncodedDict(), nullable=False)
)


def _mark_the_last_as_an_error(atomic_actions):
    """Mark the last atomic action as failed."""
    if atomic_actions:
        atomic_actions[-1]["failed"] = True
        # NOTE(andreykurilin): not all of children of the last
        #   top-level atomic should be marked as failed, only the last
        #   one, so we need recursively call
        #   `_mark_the_last_as_an_error` to find all last actions.
        _mark_the_last_as_an_error(atomic_actions[-1]["children"])


def upgrade():
    connection = op.get_bind()

    for workload in connection.execute(workload_helper.select()):
        full_data = []
        for wdata in connection.execute(workload_data_helper.select(
                workload_data_helper.c.workload_uuid == workload.uuid)):
            chunk_data = wdata.chunk_data["raw"]

            require_updating = False
            for itr in chunk_data:
                if "output" not in itr:
                    itr["output"] = {"additive": [], "complete": []}
                    if ("scenario_output" in itr
                            and itr["scenario_output"]["data"]):
                        items = list(itr["scenario_output"]["data"].items())
                        itr["output"]["additive"].append(
                            {"items": items,
                             "title": "Scenario output",
                             "description": "",
                             "chart": "OutputStackedAreaChart"})
                        del itr["scenario_output"]
                    require_updating = True
                if isinstance(itr["atomic_actions"], dict):
                    new_atomic_actions = []
                    started_at = itr["timestamp"]
                    for name, d in itr["atomic_actions"].items():
                        finished_at = started_at + d
                        new_atomic_actions.append(
                            {"name": name,
                             "children": [],
                             "started_at": started_at,
                             "finished_at": finished_at})
                        started_at = finished_at
                    itr["atomic_actions"] = new_atomic_actions
                    require_updating = True

                if itr.get("error"):
                    _mark_the_last_as_an_error(itr["atomic_actions"])
                    require_updating = True

            if require_updating:
                connection.execute(workload_data_helper.update().where(
                    workload_data_helper.c.uuid == wdata.uuid).values(
                    chunk_data={"raw": chunk_data}))

            full_data.extend(chunk_data)

        if full_data:
            full_data.sort(key=lambda itr: itr["timestamp"])

            start_time = full_data[0]["timestamp"]

            durations_stat = charts.MainStatsTable(
                {"total_iteration_count": len(full_data)})

            for itr in full_data:
                durations_stat.add_iteration(itr)

            connection.execute(workload_helper.update().where(
                workload_helper.c.uuid == workload.uuid).values(
                start_time=start_time,
                statistics={"durations": durations_stat.to_dict()}))


def downgrade():
    raise exceptions.DowngradeNotSupported()
