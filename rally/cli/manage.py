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

"""CLI interface for Rally DB management."""

from __future__ import print_function

import contextlib
import sys

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import db


@contextlib.contextmanager
def output_migration_result(method_name):
    """Print migration result."""
    print("%s started." % method_name.capitalize())
    start_revision = db.schema_revision()
    yield
    print("%s processed." % method_name.capitalize())
    current_revision = db.schema_revision()
    if start_revision != current_revision:
        print("Database migrated successfully "
              "from {start} to {end} revision.".format(start=start_revision,
                                                       end=current_revision))
    else:
        print("Database is already up to date")


class DBCommands(object):
    """Commands for DB management."""

    def recreate(self, api):
        """Drop and create Rally database.

        This will delete all existing data.
        """
        db.schema_cleanup()
        db.schema_create()
        envutils.clear_env()

    def create(self, api):
        """Create Rally database."""
        db.schema_create()

    def upgrade(self, api):
        """Upgrade Rally database to the latest state."""
        with output_migration_result("upgrade"):
            db.schema_upgrade()

    def revision(self, api):
        """Print current Rally database revision UUID."""
        print(db.schema_revision())


def main():
    categories = {"db": DBCommands}
    return cliutils.run(sys.argv, categories, skip_db_check=True)


if __name__ == "__main__":
    sys.exit(main())
