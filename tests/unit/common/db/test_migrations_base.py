# Copyright 2010-2011 OpenStack Foundation
# Copyright 2012-2013 IBM Corp.
# Copyright 2016: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
#
# Ripped off from Murano's test_migrations.py
#
# There is an ongoing work to extact similar code to oslo incubator. Once it is
# extracted we'll be able to remove this file and use oslo.

import io
import os

from alembic import command
from alembic import config as alembic_config
from alembic import migration
from alembic import script as alembic_script
from oslo_config import cfg

import rally.common.db.sqlalchemy.api
from rally.common.i18n import _LE
from rally.common import logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseWalkMigrationMixin(object):

    ALEMBIC_CONFIG = alembic_config.Config(
        os.path.join(os.path.dirname(rally.common.db.sqlalchemy.api.__file__),
                     "alembic.ini")
    )

    ALEMBIC_CONFIG.rally_config = CONF

    def _configure(self, engine):
        """Configure database connection.

        For each type of repository we should do some of configure steps.
        For migrate_repo we should set under version control our database.
        For alembic we should configure database settings. For this goal we
        should use oslo.config and openstack.commom.db.sqlalchemy.session with
        database functionality (reset default settings and session cleanup).
        """
        CONF.set_override("connection", str(engine.url), group="database")

    def _alembic_command(self, alembic_command, engine, *args, **kwargs):
        """Call alembic command.

        Most of alembic command return data into output.
        We should redefine this setting for getting info.
        """
        self.ALEMBIC_CONFIG.stdout = buf = io.StringIO()
        CONF.set_override("connection", str(engine.url), group="database")
        getattr(command, alembic_command)(*args, **kwargs)
        res = buf.getvalue().strip()
        LOG.debug("Alembic command `{command}` returns: {result}".format(
            command=alembic_command, result=res))
        return res

    def _up_and_down_versions(self):
        """Get revisions versions.

        Since alembic version has a random algorithm of generation
        (SA-migrate has an ordered autoincrement naming) we should store
        a tuple of versions (version for upgrade and version for downgrade)
        for successful testing of migrations in up>down>up mode.
        """

        env = alembic_script.ScriptDirectory.from_config(self.ALEMBIC_CONFIG)
        versions = []
        for rev in env.walk_revisions():
            if (rev.revision ==
                    rally.common.db.sqlalchemy.api.INITIAL_REVISION_UUID):
                # NOTE(rpromyshlennikov): we skip initial migration here
                continue
            versions.append((rev.revision, rev.down_revision or "-1"))

        versions.reverse()
        return versions

    def walk_versions(self, engine=None, snake_walk=False, downgrade=True):
        """Walk through versions.

        Determine latest version script from the repo, then
        upgrade from 1 through to the latest, with no data
        in the databases. This just checks that the schema itself
        upgrades successfully.
        """

        self._configure(engine)
        up_and_down_versions = self._up_and_down_versions()
        for ver_up, ver_down in up_and_down_versions:
            # upgrade -> downgrade -> upgrade
            self._migrate_up(engine, ver_up, with_data=True)
            if snake_walk:
                downgraded = self._migrate_down(engine,
                                                ver_down,
                                                with_data=True,
                                                next_version=ver_up)
                if downgraded:
                    self._migrate_up(engine, ver_up)

        if downgrade:
            # Now walk it back down to 0 from the latest, testing
            # the downgrade paths.
            up_and_down_versions.reverse()
            for ver_up, ver_down in up_and_down_versions:
                # downgrade -> upgrade -> downgrade
                downgraded = self._migrate_down(engine,
                                                ver_down, next_version=ver_up)

                if snake_walk and downgraded:
                    self._migrate_up(engine, ver_up)
                    self._migrate_down(engine, ver_down, next_version=ver_up)

    def _get_version_from_db(self, engine):
        """Return latest version for each type of migrate repo from db."""
        conn = engine.connect()
        try:
            context = migration.MigrationContext.configure(conn)
            version = context.get_current_revision() or "-1"
        finally:
            conn.close()
        return version

    def _migrate(self, engine, version, cmd):
        """Base method for manipulation with migrate repo.

        It will upgrade or downgrade the actual database.
        """

        self._alembic_command(cmd, engine, self.ALEMBIC_CONFIG, version)

    def _migrate_down(self, engine, version, with_data=False,
                      next_version=None):
        """Migrate down to a provided version of the db."""
        try:
            self._migrate(engine, version, "downgrade")
        except NotImplementedError:
            # NOTE(sirp): some migrations, namely release-level
            # migrations, don't support a downgrade.
            return False
        self.assertEqual(version, self._get_version_from_db(engine))

        # NOTE(sirp): `version` is what we're downgrading to (i.e. the 'target'
        # version). So if we have any downgrade checks, they need to be run for
        # the previous (higher numbered) migration.
        if with_data:
            post_downgrade = getattr(
                self, "_post_downgrade_%s" % next_version, None)
            if post_downgrade:
                post_downgrade(engine)

        return True

    def _migrate_up(self, engine, version, with_data=False):
        """Migrate up to a new version of the db.

        We allow for data insertion and post checks at every
        migration version with special _pre_upgrade_### and
        _check_### functions in the main test.
        """
        # NOTE(sdague): try block is here because it's impossible to debug
        # where a failed data migration happens otherwise
        check_version = version
        try:
            if with_data:
                data = None
                pre_upgrade = getattr(
                    self, "_pre_upgrade_%s" % check_version, None)
                if pre_upgrade:
                    data = pre_upgrade(engine)
            self._migrate(engine, version, "upgrade")
            self.assertEqual(version, self._get_version_from_db(engine))
            if with_data:
                check = getattr(self, "_check_%s" % check_version, None)
                if check:
                    check(engine, data)
        except Exception:
            LOG.error(_LE("Failed to migrate to version {ver} on engine {eng}")
                      .format(ver=version, eng=engine))
            raise
