# Copyright 2026: Mirantis Inc.
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

"""Base test case for the CLI command tests.

The commands are driven through :func:`rally.cli.main.main` -- the real console
entry point -- so a test exercises the *complete* flow: argument parsing (with
the multi-value / ``ArgumentOrKeyword`` wiring), the ``bootstrap`` callback,
the command body, and the Rally error-to-exit-code translation.  Only the
API object ``bootstrap`` builds is swapped for a fake; nothing else is stubbed.
"""

import contextlib
import dataclasses
import io
import os
import sys
from unittest import mock

from oslo_config import fixture as cfg_fixture  # noqa: TID251

from rally.cli import cliutils
from rally.cli import main as cli_main
from rally.common import db
from tests.unit import test


class _TeeIO(io.StringIO):
    """A ``StringIO`` that also mirrors every write into a shared buffer.

    Used to capture stdout and stderr separately while preserving the true
    interleaving order in the shared ``output`` buffer - concatenating the two
    afterwards would reorder lines that were printed one after another.
    """

    def __init__(self, shared: io.StringIO) -> None:
        super().__init__()
        self._shared = shared

    def write(self, s: str) -> int:
        self._shared.write(s)
        return super().write(s)


def _route(func, stream):
    """Wrap ``print_list``/``print_dict`` to default their ``out`` stream.

    Those helpers capture ``out=sys.stdout`` as a default argument at import
    time, so a later ``sys.stdout`` patch never reaches them.  Wrapping the
    module attribute (which commands look up as ``cliutils.print_list`` at call
    time) lets the harness send their output to the captured stream.
    """
    def wrapper(*args, **kwargs):
        kwargs.setdefault("out", stream)
        return func(*args, **kwargs)
    return wrapper


@dataclasses.dataclass(kw_only=True)
class Result:
    """Outcome of a CLI invocation."""

    exit_code: int
    stdout: str
    stderr: str
    output: str


class CLITestCase(test.TestCase):
    """Base for CLI command tests: run the real CLI against a real DB."""

    #: Create the DB schema in ``setUp``.  Commands that never touch the DB
    #: (``db``/``plugin``/``version``) can flip this off to skip the cost.
    APPLY_DB_SCHEMA = True

    def setUp(self) -> None:
        super(CLITestCase, self).setUp()
        # CONF is a process-wide singleton shared across the whole test run;
        # isolate our changes with the oslo fixture (auto-reverted on cleanup)
        # and pin the DB at in-memory SQLite so nothing hits a real database.
        conf = self.useFixture(cfg_fixture.Config()).conf
        db_url = os.environ.get("RALLY_UNITTEST_DB_URL", "sqlite://")
        conf.set_default("connection", db_url, group="database")
        # drop any engine from a previous connection, then (re)build schema.
        db.engine_reset()
        if self.APPLY_DB_SCHEMA:
            db.schema.schema_cleanup()
            db.schema.schema_create()
        self.addCleanup(db.engine_reset)

    def invoke(self, args: list[str],
               env: dict[str, str] | None = None) -> Result:
        """Run ``rally <args>`` end to end and capture the outcome.

        ``env`` overlays the given variables onto ``os.environ`` for the run
        (e.g. ``RALLY_DEPLOYMENT``), so options with ``envvar=`` defaults can
        be exercised without hand-rolling ``mock.patch.dict``.
        """
        output = io.StringIO()
        out = _TeeIO(output)
        err = _TeeIO(output)
        exit_code = 0
        with contextlib.ExitStack() as stack:
            if env is not None:
                stack.enter_context(mock.patch.dict(os.environ, env))
            stack.enter_context(
                mock.patch.object(cli_main.envutils, "load_globals"))
            # plain print() reads sys.stdout at call time -> patching it works.
            stack.enter_context(mock.patch.object(sys, "stdout", out))
            stack.enter_context(mock.patch.object(sys, "stderr", err))
            # print_list/print_dict bind out=sys.stdout as a default at import
            # time, so patching sys.stdout can't reach them; route them to the
            # captured stream instead.
            stack.enter_context(mock.patch.object(
                cliutils, "print_list", _route(cliutils.print_list, out)))
            stack.enter_context(mock.patch.object(
                cliutils, "print_dict", _route(cliutils.print_dict, out)))
            try:
                cli_main.main(args)
            except SystemExit as e:
                code = e.code
                if isinstance(code, int):
                    exit_code = code
                elif code is None:
                    exit_code = 0
                else:
                    exit_code = 1

        return Result(
            exit_code=exit_code,
            stdout=out.getvalue(),
            stderr=err.getvalue(),
            output=output.getvalue()
        )
