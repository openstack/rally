# Copyright 2013: Mirantis Inc.
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

from __future__ import print_function

import re

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import cfg
from rally.common import db


class DBCommands(object):
    """CLI commands for DB management."""

    def recreate(self, api):
        """Drop and create Rally database.

        This will delete all existing data.
        """
        print("Recreating database: ", end="")
        self.show(api, True)
        db.schema.schema_cleanup()
        print("Database deleted successfully")
        db.schema.schema_create()
        print("Database created successfully")
        envutils.clear_env()

    def create(self, api):
        """Create Rally database."""
        print("Creating database: ", end="")
        self.show(api, True)
        db.schema.schema_create()
        print("Database created successfully")

    def ensure(self, api):
        """Creates Rally database if it doesn't exists."""
        print("Ensuring database exists: ", end="")
        self.show(api, True)

        if not db.schema.schema_revision():
            db.schema.schema_create()
            print("Database created successfully")
        else:
            print("Database already exists, nothing to do")

    def upgrade(self, api):
        """Upgrade Rally database to the latest state."""
        print("Upgrading database: ", end="")
        self.show(api, True)

        start_revision = db.schema.schema_revision()
        db.schema.schema_upgrade()
        current_revision = db.schema.schema_revision()
        if start_revision != current_revision:
            print("Database schema upgraded successfully "
                  "from {start} to {end} revision."
                  .format(start=start_revision, end=current_revision))
        else:
            print("Database is already up to date")

    def revision(self, api):
        """Print current Rally database revision UUID."""
        print(db.schema.schema_revision())

    @cliutils.args("--creds", action="store_true", dest="show_creds",
                   help="Do not hide credentials from connection string")
    def show(self, api, show_creds=False):
        """Show the connection string."""
        if not show_creds:
            print(re.sub("//[^@]*@", "//**:**@", cfg.CONF.database.connection))
        else:
            print(cfg.CONF.database.connection)
