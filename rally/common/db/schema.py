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

import os

import alembic
import alembic.config
import alembic.migration
import alembic.script
import sqlalchemy as sa
import sqlalchemy.schema  # noqa

from rally.common.db import api
from rally.common.db import models
from rally import exceptions


INITIAL_REVISION_UUID = "ca3626f62937"


def _alembic_config():
    path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    config = alembic.config.Config(path)
    return config


def schema_cleanup():
    """Drop all database objects.

    Drops all database objects remaining on the default schema of the given
    engine. Per-db implementations will also need to drop items specific to
    those systems, such as sequences, custom types (e.g. pg ENUM), etc.
    """
    engine = api.get_engine()
    with engine.begin() as conn:
        inspector = sa.inspect(engine)
        metadata = sa.schema.MetaData()
        tbs = []
        all_fks = []

        for table_name in inspector.get_table_names():
            fks = []
            for fk in inspector.get_foreign_keys(table_name):
                if not fk["name"]:
                    continue
                fks.append(
                    sa.schema.ForeignKeyConstraint((), (), name=fk["name"]))
            table = sa.schema.Table(table_name, metadata, *fks)
            tbs.append(table)
            all_fks.extend(fks)

        if engine.name != "sqlite":
            for fkc in all_fks:
                conn.execute(sa.schema.DropConstraint(fkc))
        for table in tbs:
            conn.execute(sa.schema.DropTable(table))

        if engine.name == "postgresql":
            sqla_100 = int(sa.__version__.split(".")[0]) >= 1

            if sqla_100:
                enums = [e["name"] for e in sa.inspect(conn).get_enums()]
            else:
                enums = conn.dialect._load_enums(conn).keys()

            for e in enums:
                conn.execute("DROP TYPE %s" % e)


def schema_revision(config=None, engine=None, detailed=False):
    """Current database revision.

    :param config: Instance of alembic config
    :param engine: Instance of DB engine
    :param detailed: whether to return a dict with detailed data
    :rtype detailed: bool
    :returns: Database revision
    :rtype: string
    :rtype: dict
    """
    engine = engine or api.get_engine()
    with engine.connect() as conn:
        context = alembic.migration.MigrationContext.configure(conn)
        revision = context.get_current_revision()
    if detailed:
        config = config or _alembic_config()
        sc_dir = alembic.script.ScriptDirectory.from_config(config)
        return {"revision": revision,
                "current_head": sc_dir.get_current_head()}
    return revision


def schema_upgrade(revision=None, config=None, engine=None):
    """Used for upgrading database.

    :param revision: Desired database version
    :type revision: string
    :param config: Instance of alembic config
    :param engine: Instance of DB engine
    """
    revision = revision or "head"
    config = config or _alembic_config()
    engine = engine or api.get_engine()

    if schema_revision() is None:
        schema_stamp(INITIAL_REVISION_UUID, config=config)

    alembic.command.upgrade(config, revision or "head")


def schema_create(config=None, engine=None):
    """Create database schema from models description.

    Can be used for initial installation instead of upgrade('head').
    :param config: Instance of alembic config
    :param engine: Instance of DB engine
    """
    engine = engine or api.get_engine()

    # NOTE(viktors): If we will use metadata.create_all() for non empty db
    #                schema, it will only add the new tables, but leave
    #                existing as is. So we should avoid of this situation.
    if schema_revision(engine=engine) is not None:
        raise exceptions.DBMigrationError("DB schema is already under version"
                                          " control. Use upgrade() instead")

    models.BASE.metadata.create_all(engine)
    schema_stamp("head", config=config)


def schema_stamp(revision, config=None):
    """Stamps database with provided revision.

    Don't run any migrations.
    :param revision: Should match one from repository or head - to stamp
                     database with most recent revision
    :type revision: string
    :param config: Instance of alembic config
    """
    config = config or _alembic_config()
    return alembic.command.stamp(config, revision=revision)
