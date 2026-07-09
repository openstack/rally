..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================
Adopt a modern CLI framework
============================

Rally's command-line interface is built from Rally-specific helpers and
decorators layered on top of ``oslo.config``, which itself sits on top of
``argparse``. That stack is stable and cheap to run, which is why it has
survived this long. The trouble is structural: the way it is assembled ties the
CLI to a configuration library and to a lot of hand-written argparse metadata.
This spec picks a modern, type-hint-driven CLI framework to own the CLI surface
instead. The goal is to keep the same stable, low-maintenance result we have
today, while getting rid of the four problems described below.

Problem description
===================

The ``oslo.config``-based CLI (``rally/cli/cliutils.py``) is reliable, but it
is not a good long-term base to keep building on:

* **Arguments are declared twice.** Each argument is written once in a
  ``@cliutils.args("--foo", ...)`` decorator (argparse metadata, by hand) and
  once more in the function signature. The two have to be kept in sync, and
  neither of them carries any type information.

* **The signature is not the CLI contract.** Types, defaults and validation
  live in argparse ``type=``/``action=`` metadata, so static type checking does
  not cover the CLI surface at all, even though rally is otherwise fully
  mypy-gated.

* **Every argument is both positional and keyword.** ``cliutils`` registers a
  flag *and* a catch-all positional for each argument, so ``rally task start
  <cfg>`` and ``rally task start --task-config <cfg>`` behave identically. That
  ambiguity is something we would like to drop.

* **oslo.config parses the CLI as a side effect.** Parsing happens inside
  ``rally.api.API(config_args=argv[1:])`` through a registered
  ``SubCommandOpt``. In other words a configuration library ended up on the
  CLI-parsing path, which it was never designed for, hidden behind three
  abstractions and a fair amount of bespoke glue.

What we want is a replacement with the *same* stability and low running cost: a
single, well-documented layer whose public API is unlikely to shift under us.
It should address all four points — one typed declaration per argument, the
signature *as* the CLI contract, explicit control over positional-vs-keyword,
and oslo kept off the CLI-parsing path.

Proposed change
===============

Adopt a modern, type-hint-driven CLI framework and let it own the whole CLI
surface: parsing, help, strict rejection of unknown arguments and commands, and
shell completion. ``oslo.config``/``oslo.log`` go back to doing only what they
are good at — config-file loading and logging setup — fed a reconstructed
argv slice.

Requirements
------------

Whatever we choose has to provide:

* Command groups and sub-commands.
* Type hints as the source of truth for parameters.
* Global options (e.g. ``--config-file`` / ``--config-dir``).
* Dynamically-declared options, so we can expose the ``oslo.log`` library's own
  CLI arguments.
* ``-`` for stdin; a few positional primary-ids that also work as flags;
  space-separated multi-value options (``--tag a b c``); both ``rally
  --version`` and ``rally version``; Unix exit codes; and a bare group or an
  unknown command must error out (non-zero) rather than silently print help.
* Shell completion and generated docs.
* Apache-2.0-compatible licensing.
* Python 3.10+ (Rally's supported range).
* A well-maintained project with a stable interface and good adoption.

Common design
-------------

A few pieces come out the same regardless of which framework we pick, so they
are stated once here. Each option below then only shows *how* it expresses
them.

**Global options** apply to every command and sit between the program name and
the sub-command — ``rally --debug --config-file ~/.rally/rally.ini db info``.
Both frameworks expose them through a top-level *callback* whose parameters
become the global options.

**API injection.** Most commands go through the Rally API layer, which is also
where the mandatory logging setup happens. Rather than have every command build
that itself, the callback builds ``rally.api.API`` once and passes it down to
the commands. Only the mechanism for passing it around differs.

**Logging options.** ``oslo.log`` declares a set of CLI parameters it wants
exposed (``--log-file``, ``--use-syslog``, and so on), today injected natively
through ``oslo.config``. A framework can either re-declare all of those by hand
or generate them from the live ``Opt`` objects. We generate them, so the set
stays in sync with whatever ``oslo.log`` offers.

**Persisted defaults.** ``rally <thing> use <id>`` records a default in
``~/.rally/globals``. The callback copies that file into ``os.environ`` before
the sub-command is parsed, so a primary-id declared with an env var and no
default ends up required *unless* a stored default exists. Either way, both
frameworks then emit a native "missing argument" error when there is nothing to
fall back on.

Option 1: typer
---------------

typer (0.26.8, MIT) is a type-hint-first CLI framework with wide adoption; it
comes out of the FastAPI ecosystem. As of the current version its argument
parser is bundled rather than pulled in as a separate dependency, which removes
one moving part and makes the whole thing more predictable. Parameters are
declared as annotated function arguments.

Command structure
~~~~~~~~~~~~~~~~~~

Each group is a ``typer.Typer`` of plain functions. ``typer.Argument`` marks
the intentional positionals, and everything else is a ``typer.Option``:

.. code-block:: python

    @task_app.command()
    def status(
        # positional argument
        uuid: t.Annotated[
            str,
            typer.Argument(envvar="RALLY_TASK", help="UUID of task.")
        ],
        # keyword argument, i.e. specified as ``--detailed``
        detailed: t.Annotated[
            bool,
            typer.Option(help="Print detailed information.")
        ] = False,
    ) -> None:
        ...

Global options and common logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

typer implements the callback with ``@app.callback()``, and just as it does for
regular commands, it derives the parameters from the callback's signature:

.. code-block:: python

    @app.callback()
    def main(debug: bool = False,
             config_file: pathlib.Path | None = None):
        ...

logging options
+++++++++++++++

Because typer reads parameters from the signature, we generate the
``oslo.log`` options from the live ``Opt`` objects and attach them by
assigning a synthesised ``__signature__`` to the callback before it is
decorated. The parsed values are then turned back into an oslo argv slice:

.. code-block:: python

    opts = [*log_options.common_cli_opts, *log_options.logging_cli_opts]
    extra = [inspect.Parameter(o.dest, KEYWORD_ONLY, default=None,
                               annotation=_pytype(o)) for o in opts]
    main.__signature__ = inspect.Signature([*fixed_params, *extra])
    # typer now renders --log-file/--log-dir/... ; the callback rebuilds
    # ['--log-file', value, ...] and passes it to rally.api.API.

It is a bit of a trick, but it works and it stays contained.

API injection
+++++++++++++

typer ships a built-in per-run context (``ctx.obj``), but it is typed as
``typing.Any``, so static checkers cannot resolve API calls through it
without a cast:

.. code-block:: python

    @app.callback()
    def main(ctx: typer.Context, debug: bool = False,
             config_file: pathlib.Path | None = None):
        ctx.obj = rally.api.API(plugin_paths=[config_file])

    @task_app.command()
    def status(ctx: typer.Context, uuid: ...) -> None:
        rally_api: "rally.api.API" = ctx.obj      # explicit cast needed

A more type-strict alternative stores the API in a ``ContextVar`` instead:

.. code-block:: python

    _api: ContextVar[rally.api.API] = ContextVar("rally_api")

    def get_api() -> rally.api.API:               # typed accessor
        return _api.get()

    @app.callback()
    def main(debug: bool = False,
             config_file: pathlib.Path | None = None):
        _api.set(rally.api.API(plugin_paths=[config_file]))

    @task_app.command()
    def status(uuid: ...) -> None:
        rally_api = get_api()                     # already typed

The callback only runs when a sub-command is actually invoked. ``--help``,
``--version`` and the missing/unknown-command errors are all resolved by typer
before that point, so the API is never built for them.

Help and error handling
~~~~~~~~~~~~~~~~~~~~~~~~~

Here typer's defaults already do the right thing, with no extra code:

* an unknown command — even with ``--help`` — fails with ``No such command
  'foo'.`` and a non-zero exit;
* a bare group (``rally``, ``rally task``) or a command missing a required
  argument fails with ``Missing command.`` / ``Missing option '--uuid'`` on
  stderr, again non-zero.

Both are proper errors the user (and scripts, via the exit code) can act on,
rather than a success-exit usage dump that reads like ordinary help.

Multi-value options
~~~~~~~~~~~~~~~~~~~~

typer options are repeated-flag by default: a ``list[str]`` accepts
``--tag a --tag b``, but the space-separated ``--tag a b c`` fails with "Got
unexpected extra argument(s)". Supporting the space-separated form is not built
in — it needs a custom option class whose parser consumes the following
tokens up to the next flag.

Bash completion
~~~~~~~~~~~~~~~~

typer installs a small shim that, on TAB, re-invokes ``rally`` to resolve the
completions at runtime. For rally that means paying the process import cost
(~1 s) on every TAB, which is too slow to ship as-is. So we keep doing what we
do today: generate and ship a static completion file, and treat typer's runtime
completion as opt-in.

stdin
~~~~~

``rally task start`` / ``validate`` keep the ``-`` sentinel ("read from
stdin"). The value is a plain ``typer.Argument`` and the reader handles ``-``
itself.

Option 2: cyclopts
------------------

cyclopts (4.20.0, Apache-2.0) is a modern, typing-first CLI framework built
without legacy baggage, under active development, and maintained mostly by a
single author. Like typer, it derives its parameters from function signatures.

Command structure
~~~~~~~~~~~~~~~~~~

Each group is a ``cyclopts.App`` of plain functions. Positional-vs-keyword is
controlled with ``*``, and public names / env vars come from
``cyclopts.Parameter``:

.. code-block:: python

    @task_app.command
    def status(
        # positional argument
        uuid: t.Annotated[
            str,
            cyclopts.Parameter(env_var="RALLY_TASK", help="UUID of task.")
        ],
        *,  # everything after is keyword-only
        detailed: t.Annotated[
            bool,
            cyclopts.Parameter(help="Print detailed information.")
        ] = False,
    ) -> None:
        ...

Global options and common logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

cyclopts implements the callback as a *meta app* (``@app.meta.default``); its
parameters become the global options:

.. code-block:: python

    @app.meta.default
    def main(*tokens, debug: bool = False,
             config_file: pathlib.Path | None = None):
        ...

logging options
+++++++++++++++

cyclopts can expand a dataclass onto the meta app, so we generate the
``oslo.log`` options as a real dataclass and let it flatten them — through a
documented extension point, and without touching ``__signature__``:

.. code-block:: python

    Globals = dataclasses.make_dataclass(
        "Globals",
        [(o.dest, t.Annotated[_pytype(o),
                              cyclopts.Parameter(name="--" + o.name)])
         for o in opts])
    # flattened onto app.meta with Parameter(name="*")

This is cleaner than typer's ``__signature__`` assignment.

API injection
+++++++++++++

cyclopts injects a value by type. A private ``_``-prefixed parameter is skipped
during parsing (``parse="^(?!_)"``) and then filled from the ``ignored``
mapping that ``parse_args`` returns:

.. code-block:: python

    app = cyclopts.App(
        default_parameter=cyclopts.Parameter(parse="^(?!_)"))

    @task_app.command
    def status(*, uuid: str, _api: rally.api.API) -> None: ...

    @app.meta.default
    def main(*tokens) -> int:
        api = rally.api.API(...)
        command, bound, ignored = app.parse_args(tokens)
        for name, type_ in ignored.items():
            if type_ is rally.api.API:
                bound.arguments[name] = api
        return command(*bound.args, **bound.kwargs)

The same ``ContextVar`` approach shown for typer works here too, and it is more
type-strict than the ``_api`` parameter.

Help and error handling
~~~~~~~~~~~~~~~~~~~~~~~~~

This is where cyclopts falls short for us: its defaults do **not** match what
we want, and correcting them needs code that reaches into internals.

``--help`` is eager, so an unknown command with ``--help`` (``rally foo
--help``) prints the *root* help and exits 0 instead of erroring. To work
around that we scan the argv, walk the command tree and strip ``--help`` so
cyclopts falls back to its native "unknown command" error:

.. code-block:: python

    if "--help" in tokens and _unknown_command(tokens):
        tokens = tuple(t for t in tokens if t != "--help")

A bare group (``rally verify``) prints the group help and exits 0 (success),
because cyclopts resolves it to its internal ``help_print``. To make it fail
instead, we detect that and render an error panel by hand:

.. code-block:: python

    command, bound, ignored = app.parse_args(tokens)
    if getattr(command, "__func__", None) is cyclopts.App.help_print:
        app.error_console.print(cyclopts.panel.CycloptsPanel(
            cyclopts.CycloptsError(msg="Missing command.")))
        return 2

Neither workaround is large, but both lean on cyclopts internals — which is
exactly the sort of thing that tends to break on an upgrade.

Multi-value options
~~~~~~~~~~~~~~~~~~~~

cyclopts supports the space-separated form natively: ``consume_multiple=True``
lets a single flag take several values (``--tag a b c``), matching the old
argparse ``nargs="+"``. Repeated flags (``--tag a --tag b``) work too.

.. code-block:: python

    cyclopts.Parameter(consume_multiple=True)

Bash completion
~~~~~~~~~~~~~~~~

cyclopts' ``generate_completion`` produces a *static* script that bakes in the
whole command tree (fast, no runtime cost). The catch is that it enumerates
every parameter — including the injected ``_api``/``--g`` — and cannot hide
them with ``Parameter(show=False)``. Moving the API to a ``ContextVar``
removes the leak. The script still goes stale on any CLI change and has to be
regenerated, the same as typer's.

stdin
~~~~~

Same ``-`` sentinel as typer; the value is a positional argument and the reader
handles ``-``.

Alternatives
------------

* **Keep the ``oslo.config`` CLI as-is.** No work, and already proven in
  production. But it keeps all four problems above and is not a modern,
  type-driven base to build on.
* **Drop down to raw ``argparse``.** This removes the oslo layer, but
  ``argparse`` is not a modern solution and does not expose the CLI as typed
  signatures, so we would lose the mypy-covered contract that motivates the
  change in the first place.

Conclusion
----------

Both typer and cyclopts satisfy the requirements and both give us typed
signatures. Weighing the aspects above:

**typer pros**

* Help/error handling matches our needs out of the box — unknown command,
  bare group and missing argument all fail with a clear message and a non-zero
  exit, with no custom code and nothing relying on library internals.
* Larger adoption and a mature, bundled parser, which makes for a more
  predictable long-term base than a single-maintainer library.

**cyclopts pros**

* Global options generate cleanly as a dataclass, with no ``__signature__``
  assignment. (This surface is temporary anyway — the logging flags are being
  reduced to a small hand-written set.)
* Positional-vs-keyword follows native Python style: it honours the ``*``
  keyword-only marker, so the signature reads as plain Python. typer decides
  purely on whether a default is present (no default -> positional, default ->
  option) and ignores ``*`` entirely.

**Neutral**

* Shell completion — a wash. Both end up shipping a generated static file.
* Multi-value options — native (space-separated) in cyclopts, a custom Option
  class in typer. That said, repeating ``--tag`` is arguably the better
  long-term idiom, so we are not counting this against typer.
* Both are typed, permissively licensed, Python 3.10+, and actively developed.

**Winner: typer.** Its help/error ergonomics and its stable, broadly-adopted
base come with the fewest custom moving parts. cyclopts' edges (dataclass
globals, Python-native argument style) are real, but they do not outweigh
needing internal-reaching hacks for behaviour that typer gives us by default.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  andreykurilin

Work Items
----------

Delivered as separate commits (the last two may be swapped):

* Port the CLI to typer, keeping it as backward-compatible as we reasonably
  can: app skeleton, callback with API injection and the generated
  ``oslo.log`` options, all six command groups, persisted-global defaults,
  ``-`` stdin, and a generated completion file — with the functional suite
  kept green throughout.
* Backward-incompatible cleanup: reduce the logging CLI flags to a small
  hand-written set (the daemon options remain, via ``rally.conf``) and settle
  multi-value on repeated flags, dropping the compatibility shims.
* Rewrite the CLI unit tests so they drive the app through
  ``typer.testing.CliRunner`` instead of calling the command functions
  directly.

Dependencies
============

* Adds a runtime dependency on ``typer`` (>= 0.26, Python >= 3.10, MIT).
  It pulls in ``rich``, ``shellingham``, ``annotated-doc``, ``markdown-it-py``,
  ``mdurl`` and ``Pygments`` — all permissive, none copyleft.
* Continues to depend on ``oslo.config`` / ``oslo.log``, but only for
  config-file loading and logging setup now, not for CLI parsing.

References
==========

* typer documentation: https://typer.tiangolo.com
