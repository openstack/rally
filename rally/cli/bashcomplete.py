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

import itertools


_HEADER = r"""#!/bin/bash

# Standalone _filedir() alternative.
# This exempts from dependence of bash completion routines
function _rally_filedir()
{
    test "${1}" \
        && COMPREPLY=( \
            $(compgen -f -- "${cur}" | grep -E "${1}") \
            $(compgen -o plusdirs -- "${cur}") ) \
        || COMPREPLY=( \
            $(compgen -o plusdirs -f -- "${cur}") \
            $(compgen -d -- "${cur}") )
}

_rally()
{
    declare -A SUBCOMMANDS
    declare -A OPTS

"""

_FOOTER = r"""    for OPT in ${!OPTS[*]} ; do
        CMD=${OPT%%_*}
        CMDSUB=${OPT#*_}
        SUBCOMMANDS[${CMD}]+="${CMDSUB} "
    done

    COMMANDS="${!SUBCOMMANDS[*]}"
    COMPREPLY=()

    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ $cur =~ ^(\.|\~|\/) ]] || [[ $prev =~ ^--out(|put-file)$ ]] ; then
        _rally_filedir
    elif [[ $prev =~ ^--(task|filename)$ ]] ; then
        _rally_filedir "\.json|\.yaml|\.yml"
    elif [ $COMP_CWORD == "1" ] ; then
        COMPREPLY=($(compgen -W "$COMMANDS" -- ${cur}))
    elif [ $COMP_CWORD == "2" ] ; then
        COMPREPLY=($(compgen -W "${SUBCOMMANDS[${prev}]}" -- ${cur}))
    else
        COMMAND="${COMP_WORDS[1]}_${COMP_WORDS[2]}"
        COMPREPLY=($(compgen -W "${OPTS[$COMMAND]}" -- ${cur}))
    fi
    return 0
}

complete -o filenames -F _rally rally
"""

def generate() -> str:
    """Return the bash completion script for the current CLI."""
    import typer

    from rally.cli import cliutils
    from rally.cli import main

    # ``typer.main.get_command`` builds the resolved command tree; we read the
    # flags there rather than from ``registered_commands`` because typer stores
    # a declared flag on the raw ``typer.Option`` ambiguously -- an Annotated
    # positional flag lands in ``OptionInfo.default``, not ``param_decls`` --
    # so only the built command exposes the correct ``--flags``.
    command = typer.main.get_command(main.app)
    lines = []
    for path, _leaf, params in cliutils.iter_commands(command):
        if len(path) != 2:
            # top-level leaf command (e.g. ``version``) -- no OPTS entry
            continue
        category, name = path
        opts = " ".join(
            itertools.chain.from_iterable(
                (
                    # only long ``--flags``; short aliases (``-n``) are valid
                    # but kept out of completion
                    name for name in p.opts
                    if (name.startswith("--")
                        and name not in ("--help", "--version"))
                )
                for p in params
            ))

        lines.append(f'    OPTS["{category}_{name}"]="{opts}"\n')
    return _HEADER + "".join(sorted(lines)) + _FOOTER
