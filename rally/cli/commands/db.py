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

import re
import typing as t

import typer

from rally.cli import envutils
from rally.common import cfg
from rally.common import db


db_app = typer.Typer(
    name="db", no_args_is_help=False,
    help="Create, upgrade and inspect the database.")


def _print_connection(show_creds: bool) -> None:
    if show_creds:
        print(cfg.CONF.database.connection)
    else:
        print(re.sub("//[^@]*@", "//**:**@", cfg.CONF.database.connection))


@db_app.command()
def recreate() -> None:
    """Drop and create Rally database.

    This will delete all existing data.
    """
    print("Recreating database: ", end="")
    _print_connection(True)
    db.schema.schema_cleanup()
    print("Database deleted successfully")
    db.schema.schema_create()
    print("Database created successfully")
    envutils.clear_env()


@db_app.command()
def create() -> None:
    """Create Rally database."""
    print("Creating database: ", end="")
    _print_connection(True)
    db.schema.schema_create()
    print("Database created successfully")


@db_app.command()
def ensure() -> None:
    """Create Rally database if it doesn't exist."""
    print("Ensuring database exists: ", end="")
    _print_connection(True)

    if not db.schema.schema_revision():
        db.schema.schema_create()
        print("Database created successfully")
    else:
        print("Database already exists, nothing to do")


@db_app.command()
def upgrade() -> None:
    """Upgrade Rally database to the latest state."""
    print("Upgrading database: ", end="")
    _print_connection(True)

    start_revision = db.schema.schema_revision()
    db.schema.schema_upgrade()
    current_revision = db.schema.schema_revision()
    if start_revision != current_revision:
        print("Database schema upgraded successfully "
              "from {start} to {end} revision."
              .format(start=start_revision, end=current_revision))
    else:
        print("Database is already up to date")


@db_app.command()
def revision() -> None:
    """Print current Rally database revision UUID."""
    print(db.schema.schema_revision())


@db_app.command()
def show(
    creds: t.Annotated[
        bool,
        typer.Option(
            "--creds",
            help="Do not hide credentials from connection string"
        )
    ] = False,
) -> None:
    """Show the connection string."""
    _print_connection(creds)
