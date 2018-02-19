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

"""update-contexts

Revision ID: dc46687661df
Revises: 4394bdc32cfd
Create Date: 2017-10-24 15:50:17.493354

"""

from alembic import op
import sqlalchemy as sa

from rally.common.db import sa_types
from rally import exceptions
from rally import plugins
from rally.task import context

# revision identifiers, used by Alembic.
revision = "dc46687661df"
down_revision = "4394bdc32cfd"
branch_labels = None
depends_on = None


subtask_helper = sa.Table(
    "subtasks",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("context", sa_types.MutableJSONEncodedDict()),
    sa.Column("contexts", sa_types.MutableJSONEncodedDict()),
    sa.Column("contexts_results", sa_types.MutableJSONEncodedList())
)

workload_helper = sa.Table(
    "workloads",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("task_uuid", sa.String(length=36), nullable=False),
    sa.Column("context", sa_types.MutableJSONEncodedDict()),
    sa.Column("contexts", sa_types.MutableJSONEncodedDict()),
    sa.Column("contexts_results", sa_types.MutableJSONEncodedList()),
    sa.Column("start_time", sa_types.TimeStamp),
    sa.Column("created_at", sa.DateTime),
    sa.Column("load_duration", sa.Float),
    sa.Column("full_duration", sa.Float),
)


def _process_contexts(w_context):
    """Put the contexts setup and cleanup methods in the order of execution."""
    try:
        plugins.load()
        ctxs = []
        for ctx_name in w_context:
            ctx_cls = context.Context.get(ctx_name)
            ctxs.append((ctx_cls.get_order(), ctx_cls.get_fullname()))
        ctxs.sort()
        ctxs = ["%s.setup" % ctx_name for _i, ctx_name in ctxs]
        ctxs.extend([ctx.replace(".setup", ".cleanup")
                     for ctx in reversed(ctxs)])
        return ctxs
    except Exception:
        # the proper of context can be missed while applying the migration, it
        # should not stop us from migrating the database
        return None


def upgrade():
    with op.batch_alter_table("subtasks") as batch_op:
        batch_op.add_column(sa.Column("contexts",
                                      sa_types.MutableJSONEncodedDict(),
                                      default={}, nullable=False))
        batch_op.add_column(sa.Column("contexts_results",
                                      sa_types.MutableJSONEncodedList(),
                                      default=[], nullable=False))
        # it was not used, so we do not need to migrate the data
        batch_op.drop_column("context")
    with op.batch_alter_table("workloads") as batch_op:
        batch_op.add_column(sa.Column("contexts",
                                      sa_types.MutableJSONEncodedDict(),
                                      default={}, nullable=False))
        batch_op.add_column(sa.Column("contexts_results",
                                      sa_types.MutableJSONEncodedList(),
                                      default=[], nullable=False))
        # it was not used, so we do not need to migrate the data
        batch_op.drop_column("context_execution")

    connection = op.get_bind()
    for workload in connection.execute(workload_helper.select()):
        # NOTE(andreykurilin): The real information about execution of contexts
        #   for previous results are missed (expected thing) and it is
        #   impossible to guess started_at and finished_at timestamps of each
        #   context. Let's do not add random data, since no data is better
        #   that the wrong one.

        if workload.start_time is None:
            # The load did not start in workload. It can mean that one of
            #   contexts had failed or some error had happened in the runner
            #   itself. In both cases, we do not have much data to do anything,
            #   so making an assumption that no contexts were executed at all.
            contexts_results = []
        else:
            # We cannot guess timings for each contexts, but we can restore
            # started_at and finished_at timings for setup and cleanup methods
            # of context manager.

            # The workload record in the database is created right before the
            # launch of ContextManage.
            ctx_setup_started_at = float(workload.created_at.strftime("%s"))
            # There is a small preparation step of a runner between finishing
            # the setup of context manager and launching the load itself. It
            # doesn't take much time, let it be 0.01 seconds
            ctx_setup_finished_at = workload.start_time - 0.01
            # The context manager starts cleanup right after the load is
            # finished. Again, there can be possible delay, let it be 0.01
            # seconds
            ctx_cleanup_started_at = (
                workload.start_time + workload.load_duration + 0.01)
            # We cannot rely on updated_at field since it can be affected by
            # another migration. The full_duration is a timestamp of the moment
            # when the load is finished, all results are saved in the database
            # and cleanup method of context manager is performed. It is not the
            # right timestamp of finishing cleanup, but it should be almost
            # there. Let's deduct 0.1 seconds.
            ctx_cleanup_finished_at = (
                ctx_setup_started_at + workload.full_duration - 0.1)

            # plugin_name and arguments should be used only for analyzing, not
            # for restoring original task itself, so we can use custom thing
            # here
            contexts_results = [{
                "plugin_name": "AllExecutedContexts",
                "plugin_cfg": {
                    "description":
                        "It is impossible to restore stats of executed "
                        "contexts while performing database migration. "
                        "The current info displays the approximate timestamps "
                        "which should say when the first setup method was "
                        "executed, when the last setup method finished, when "
                        "the first cleanup was started and when the last "
                        "cleanup finished. Also, please not that it is "
                        "impossible to guess information about possible "
                        "errors, so the current stats are marked as "
                        "successful."},
                "setup": {
                    "started_at": ctx_setup_started_at,
                    "finished_at": ctx_setup_finished_at,
                    "atomic_actions": [],
                    "error": None
                },
                "cleanup": {
                    "started_at": ctx_cleanup_started_at,
                    "finished_at": ctx_cleanup_finished_at,
                    "atomic_actions": [],
                    "error": None
                }
            }]

            possible_order = _process_contexts(workload.context)
            if possible_order:
                contexts_results[0]["plugin_cfg"]["order_of_execution"] = {
                    "note": "We do not know if all setup methods were "
                            "executed, but if they were, the following order "
                            "is right.",
                    "order": possible_order
                }

        connection.execute(
            workload_helper.update().where(
                workload_helper.c.uuid == workload.uuid).values(
                {"contexts": workload_helper.c.context,
                 "contexts_results": contexts_results}))

    with op.batch_alter_table("workloads") as batch_op:
        batch_op.drop_column("context")


def downgrade():
    raise exceptions.DowngradeNotSupported()
