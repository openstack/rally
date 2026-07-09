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

"""Primary identifiers that accept both a positional and a ``--flag`` form.

Rally has always exposed a command's primary identifier both ways, e.g.
``rally task abort <uuid>`` and ``rally task abort --uuid <uuid>``.  typer lets
a parameter be an Argument *or* an Option, not both, so
:class:`ArgumentOrKeyword` declares the positional form and :func:`install`
registers the ``--flag`` alias
directly in the parser, pointing at the same destination.  Requiredness,
env-var defaults, unknown-option and extra-argument errors all stay native --
there is no hidden duplicate parameter and no post-hoc value merging.
"""

import inspect
import typing as t

import typer
import typer.core

from rally.cli import cliutils


if t.TYPE_CHECKING:
    import typer._click.core


class ArgumentOrKeyword(typer.models.ArgumentInfo):
    """A required positional argument that is also accepted as ``--flag``.

    Use it in place of :func:`typer.Argument` and pass the legacy flag
    name(s)::

        task_id: t.Annotated[
            str,
            ArgumentOrKeyword("--uuid", envvar=envutils.ENV_TASK,
                              help="UUID of task.")
        ]

    typer builds an ordinary required Argument from it (the ``--flag`` is wired
    up later by :func:`install`); the flag itself stays out of ``--help`` and
    bash completion, so the positional form is the documented one.
    """

    def __init__(
        self,
        *kw_decls: str,
        help: str | None = None,
        envvar: str | list[str] | None = None,
        metavar: str | None = None
    ) -> None:
        if metavar is None and kw_decls:
            # ``--uuid`` -> ``UUID``, nicer in usage than the derived name.
            metavar = kw_decls[0].lstrip("-").replace("-", "_").upper()
        super().__init__(default=..., help=help, envvar=envvar,
                         metavar=metavar)
        self.kw_decls = kw_decls


def _patch_param(
    param: "typer.core.TyperOption",
    kw_decls: t.Sequence[str]
) -> None:
    """Register ``kw_decls`` as an option feeding ``param``'s destination."""
    original_add_to_parser = param.add_to_parser
    # A list argument (``nargs == -1``) accepts repeated ``--flag`` values.
    action = "append" if param.nargs == -1 else "store"

    def add_to_parser(
        parser: "typer._click.core._OptionParser",
        ctx: "typer._click.core.Context"
    ) -> None:
        original_add_to_parser(parser, ctx)
        # Don't let the (now optional) positional overwrite a value that the
        # ``--flag`` option already stored under the shared destination.
        argument = parser._args[-1]
        original_process = argument.process

        def process(value: t.Any, state: t.Any) -> None:
            if value in (None, ()) and param.name in state.opts:
                return
            original_process(value, state)
        argument.process = process  # type: ignore[method-assign]

        parser.add_option(param, list(kw_decls), param.name,
                          action=action, nargs=1)

    param.add_to_parser = add_to_parser  # type: ignore[method-assign]


def install(command: typer.core.TyperGroup | typer.core.TyperCommand) -> None:
    """Wire up every :class:`ArgumentOrKeyword` in a built command tree."""
    for _path, leaf, params in cliutils.iter_commands(command):
        if leaf.callback is None:
            continue
        signature = inspect.signature(inspect.unwrap(leaf.callback))
        marks = {}
        for name, parameter in signature.parameters.items():
            for meta in getattr(parameter.annotation, "__metadata__", ()):
                if isinstance(meta, ArgumentOrKeyword):
                    marks[name] = meta.kw_decls
        if not marks:
            continue
        for param in params:
            if param.name in marks:
                _patch_param(param, marks[param.name])
