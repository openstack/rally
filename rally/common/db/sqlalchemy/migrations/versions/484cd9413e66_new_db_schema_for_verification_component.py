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

"""Provide new db schema for verification component

Revision ID: 484cd9413e66
Revises: e654a0648db0
Create Date: 2016-11-04 17:04:24.614075

"""

# revision identifiers, used by Alembic.
revision = "484cd9413e66"
down_revision = "e654a0648db0"
branch_labels = None
depends_on = None

import uuid

from alembic import op
from oslo_utils import timeutils
import sqlalchemy as sa

from rally.common.db.sqlalchemy import types as sa_types
from rally import exceptions


TASK_STATUSES = ["aborted", "aborting", "cleaning up", "failed", "finished",
                 "init", "paused", "running", "setting up", "soft_aborting",
                 "verifying"]

_MAP_OLD_TO_NEW_TEST_STATUSES = {
    "OK": "success",
    "FAIL": "fail",
    "SKIP": "skip"
}


def UUID():
    return str(uuid.uuid4())


verification_helper = sa.Table(
    "verifications",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("uuid", sa.String(36), nullable=False),
    sa.Column("deployment_uuid", sa.String(36), nullable=False),
    sa.Column("status", sa.Enum(*TASK_STATUSES, name="enum_tasks_status"),
              default="init", nullable=False),
    sa.Column("set_name", sa.String(20)),
    sa.Column("tests", sa.Integer),
    sa.Column("errors", sa.Integer),
    sa.Column("failures", sa.Integer),
    sa.Column("time", sa.Float),
    sa.Column("created_at", sa.DateTime),
    sa.Column("updated_at", sa.DateTime)
)


results_helper = sa.Table(
    "verification_results",
    sa.MetaData(),
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("verification_uuid", sa.String(36), nullable=False),
    sa.Column("data", sa_types.MutableJSONEncodedDict, nullable=False,
              default={}),
    sa.Column("created_at", sa.DateTime),
    sa.Column("updated_at", sa.DateTime)
)


def upgrade():
    connection = op.get_bind()

    # create new table to store all verifiers
    verifiers_table = op.create_table(
        "verifiers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", sa.String(36), default=UUID, nullable=False),

        sa.Column("name", sa.String(255), unique=True),
        sa.Column("description", sa.Text),

        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("namespace", sa.String(255)),

        sa.Column("source", sa.String(255)),
        sa.Column("version", sa.String(255)),
        sa.Column("system_wide", sa.Boolean),

        sa.Column("status", sa.String(36), default="init", nullable=False),

        sa.Column("extra_settings", sa_types.MutableJSONEncodedDict,
                  nullable=True),

        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime)
    )

    op.create_index("verifier_uuid", "verifiers", ["uuid"], unique=True)

    verifications_table = op.create_table(
        "verifications_new",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("uuid", sa.String(36), default=UUID, nullable=False),

        sa.Column("verifier_uuid", sa.String(36), nullable=False),
        sa.Column("deployment_uuid", sa.String(36), nullable=False),

        sa.Column("run_args", sa_types.MutableJSONEncodedDict),

        sa.Column("status", sa.String(36), default="init", nullable=False),

        sa.Column("tests_count", sa.Integer, default=0),
        sa.Column("failures", sa.Integer, default=0),
        sa.Column("skipped", sa.Integer, default=0),
        sa.Column("success", sa.Integer, default=0),
        sa.Column("unexpected_success", sa.Integer, default=0),
        sa.Column("expected_failures", sa.Integer, default=0),
        sa.Column("tests_duration", sa.Float, default=0.0),

        sa.Column("tests", sa_types.MutableJSONEncodedDict, default={}),

        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),

        sa.ForeignKeyConstraint(["verifier_uuid"], ["verifiers.uuid"]),
        sa.ForeignKeyConstraint(["deployment_uuid"], ["deployments.uuid"])
    )

    default_verifier = None
    for vresult in connection.execute(results_helper.select()):
        if default_verifier is None:
            vuuid = UUID()
            connection.execute(
                verifiers_table.insert(),
                [{
                    "uuid": vuuid,
                    "name": "DefaultTempestVerifier",
                    "description": "It is the default verifier to assign all "
                                   "migrated verification results for",
                    "type": "tempest",
                    "namespace": "openstack",
                    "source": "n/a",
                    "version": "n/a",
                    "system_wide": False,
                    "status": "init",
                    "created_at": timeutils.utcnow(),
                    "updated_at": timeutils.utcnow()
                }]
            )
            default_verifier = connection.execute(
                verifiers_table.select().where(
                    verifiers_table.c.uuid == vuuid)).first()

        data = vresult.data
        if "errors" in data:
            # it is a very old format...
            for test in data["test_cases"].keys():
                old_status = data["test_cases"][test]["status"]
                new_status = _MAP_OLD_TO_NEW_TEST_STATUSES.get(
                    old_status, old_status.lower())
                data["test_cases"][test]["status"] = new_status

                if "failure" in data["test_cases"][test]:
                    data["test_cases"][test]["traceback"] = data[
                        "test_cases"][test]["failure"]["log"]
                    data["test_cases"][test].pop("failure")

        verifications = connection.execute(
            verification_helper.select().where(
                verification_helper.c.uuid == vresult.verification_uuid))
        # for each verification result we have single verification object
        verification = verifications.first()

        connection.execute(
            verifications_table.insert(),
            [{"uuid": verification.uuid,
              "verifier_uuid": default_verifier.uuid,
              "deployment_uuid": verification.deployment_uuid,
              "run_args": {"pattern": "set=%s" % verification.set_name},
              "status": verification.status,
              "tests": data["test_cases"],
              "tests_count": data["tests"],
              "failures": data["failures"],
              "skipped": data["skipped"],
              "success": data["success"],
              "unexpected_success": data.get("unexpected_success", 0),
              "expected_failures": data.get("expected_failures", 0),
              "tests_duration": data["time"],
              "created_at": vresult.created_at,
              "updated_at": vresult.updated_at
              }])

    op.drop_table("verification_results")
    op.drop_table("verifications")
    op.rename_table("verifications_new", "verifications")

    op.create_index(
        "verification_uuid", "verifications", ["uuid"], unique=True)


def downgrade():
    raise exceptions.DowngradeNotSupported()
