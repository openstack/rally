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

import json
import os
import traceback
import typing as t

import prettytable
import typer

from rally import exceptions
from rally.cli import argutils
from rally.cli import cliutils
from rally.cli import envutils
from rally.cli import yamlutils as yaml
from rally.env import env_mgr


env_app = typer.Typer(
    name="env", no_args_is_help=False,
    help="Environments Rally tests against.")

YES = u":-)"
NO = u":-("

MSG_NO_ENVS = ("There are no environments. To create a new environment, "
               "use command bellow to create one:\nrally env create")


def _print(msg: object, silent: bool = False) -> None:
    if not silent:
        print(msg)


def _show(env_data: dict, to_json: bool, only_spec: bool) -> None:
    if only_spec:
        print(json.dumps(env_data["spec"], indent=2))
    elif to_json:
        print(json.dumps(env_data, indent=2))
    else:
        table = prettytable.PrettyTable()
        table.header = False
        for k in ["uuid", "name", "status",
                  "created_at", "updated_at", "description"]:
            table.add_row([k, env_data[k]])

        table.add_row(["extras", json.dumps(env_data["extras"], indent=2)])
        for p, data in env_data["platforms"].items():
            table.add_row(["platform: %s" % p,
                           json.dumps(data["platform_data"], indent=2)])
        table.align = "l"
        print(table.get_string())


def _use(env_uuid: str, to_json: bool) -> None:
    _print("Using environment: %s" % env_uuid, to_json)
    envutils.update_globals_file(envutils.ENV_ENV, env_uuid)


@env_app.command()
def create(
    name: t.Annotated[
        str,
        typer.Option(
            "--name", "-n",
            help="Name of the env."
        )
    ],
    description: t.Annotated[
        str | None,
        typer.Option(
            "--description", "-d",
            help="Env description"
        )
    ] = None,
    extras: t.Annotated[
        str | None,
        typer.Option(
            "--extras", "-e",
            help="JSON or YAML dict with custom non validate info."
        )
    ] = None,
    spec: t.Annotated[
        str | None,
        typer.Option(
            "--spec", "-s",
            help="Path to env spec."
        )
    ] = None,
    from_sysenv: t.Annotated[
        bool,
        typer.Option(
            "--from-sysenv",
            help="Iterate over all available platforms and check system "
                 "environment for credentials."
        )
    ] = False,
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
    no_use: t.Annotated[
        bool,
        typer.Option(
            "--no-use",
            help="Don't set new env as default for future operations."
        )
    ] = False,
) -> None:
    """Create new environment."""
    if spec is not None and from_sysenv:
        print("Arguments '--spec' and '--from-sysenv' cannot be used "
              "together, use only one of them.")
        raise typer.Exit(code=1)
    spec_obj: t.Any = spec or {}
    if spec:
        with open(os.path.expanduser(spec), "rb") as f:
            spec_obj = yaml.safe_load(f.read())
    extras_obj = yaml.safe_load(extras) if extras else None

    if from_sysenv:
        result = env_mgr.EnvManager.create_spec_from_sys_environ()
        spec_obj = result["spec"]
        _print("Your system environment includes specifications of "
               "%s platform(s)." % len(spec_obj), to_json)
        _print("Discovery information:", to_json)
        for p_name, p_result in result["discovery_details"].items():
            _print("\t - %s : %s." % (p_name, p_result["message"]), to_json)

            if "traceback" in p_result:
                _print("".join(p_result["traceback"]), to_json)
    try:
        env = env_mgr.EnvManager.create(
            name, spec_obj, description=description, extras=extras_obj)
    except exceptions.ManagerInvalidSpec as e:
        _print("Env spec has wrong format:", to_json)
        _print(json.dumps(e.kwargs["spec"], indent=2), to_json)
        for err in e.kwargs["errors"]:
            _print(err, to_json)
        raise typer.Exit(code=1)
    except Exception:
        _print("Something went wrong during env creation:", to_json)
        _print(traceback.format_exc(), to_json)
        raise typer.Exit(code=1)

    if not no_use:
        _use(env.uuid, to_json)
    _show(env.data, to_json=to_json, only_spec=False)


@env_app.command()
def cleanup(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
) -> None:
    """Perform disaster cleanup for specified environment.

    Cases when Rally can leave undeleted resources after performing
    workload:

    - Rally execution was interrupted and cleanup was not performed
    - The environment or a particular platform became unreachable which
      fail Rally execution of cleanup
    """
    env_obj = env_mgr.EnvManager.get(env)
    _print("Cleaning up resources for %s" % env_obj, to_json)
    result = env_obj.cleanup()

    if to_json:
        print(json.dumps(result, indent=2))
        if any(p["errors"] for p in result.values()):
            raise typer.Exit(code=1)
        return

    print("Cleaning is finished. See the results bellow.")

    return_code = 0
    for platform in sorted(result):
        cleanup_info = result[platform]
        print("\nInformation for %s platform." % platform)
        print("=" * 80)
        print("Status: %s" % cleanup_info["message"])
        for key in ("discovered", "deleted", "failed"):
            print("Total %s: %s" % (key, cleanup_info[key]))
        if cleanup_info["errors"]:
            return_code = 1
            errors = "\t- ".join(e["message"]
                                 for e in cleanup_info["errors"])
            print("Errors:\n\t- %s" % errors)

    if return_code:
        raise typer.Exit(code=1)


@env_app.command()
def destroy(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    skip_cleanup: t.Annotated[
        bool,
        typer.Option(
            "--skip-cleanup",
            help="Do not perform platforms cleanup before destroy."
        )
    ] = False,
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
    detailed: t.Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show detailed information."
        )
    ] = False,
) -> None:
    """Destroy existing environment."""
    env_obj = env_mgr.EnvManager.get(env)
    _print("Destroying %s" % env_obj, to_json)
    result = env_obj.destroy(skip_cleanup)
    return_code = int(result["destroy_info"]["skipped"])

    if result["destroy_info"]["skipped"]:
        _print("%s Failed to destroy env %s: %s"
               % (NO, env_obj, result["destroy_info"]["message"]), to_json)
    else:
        _print("%s Successfully destroyed env %s" % (YES, env_obj), to_json)

    if detailed or to_json:
        print(json.dumps(result, indent=2))

    if return_code:
        raise typer.Exit(code=return_code)


@env_app.command()
def delete(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    force: t.Annotated[
        bool,
        typer.Option(
            "--force",
            help="Delete DB records even if env is not destroyed."
        )
    ] = False,
) -> None:
    """Delete all records related to the environment from db."""
    env_mgr.EnvManager.get(env).delete(force=force)


@env_app.command(name="list")
@cliutils.suppress_warnings
def list_(
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
) -> None:
    """List existing environments."""
    envs = env_mgr.EnvManager.list()
    if to_json:
        print(json.dumps([env.cached_data for env in envs], indent=2))
    elif not envs:
        print(MSG_NO_ENVS)
    else:
        cur_env = envutils.get_global(envutils.ENV_ENV)
        table = prettytable.PrettyTable()
        fields = ["uuid", "name", "status", "created_at", "description"]
        table.field_names = fields + ["default"]
        for env in envs:
            row = [env.cached_data[f] for f in fields]
            row.append(cur_env == env.cached_data["uuid"] and "*" or "")
            table.add_row(row)
        table.sortby = "created_at"
        table.reversesort = True
        table.align = "l"
        print(table.get_string())


@env_app.command()
@cliutils.suppress_warnings
def show(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
    only_spec: t.Annotated[
        bool,
        typer.Option(
            "--only-spec",
            help="Print only a spec for the environment."
        )
    ] = False,
) -> None:
    """Show base information about the environment record."""
    env_data = env_mgr.EnvManager.get(env).data
    _show(env_data, to_json=to_json, only_spec=only_spec)


@env_app.command()
def info(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
) -> None:
    """Retrieve and show environment information."""
    env_obj = env_mgr.EnvManager.get(env)
    env_info = env_obj.get_info()
    return_code = int(any(v.get("error") for v in env_info.values()))

    if to_json:
        print(json.dumps(env_info, indent=2))
        if return_code:
            raise typer.Exit(code=return_code)
        return

    table = prettytable.PrettyTable()
    table.field_names = ["platform", "info", "error"]
    for platform, data in env_info.items():
        table.add_row([
            platform, json.dumps(data["info"], indent=2),
            data.get("error") or ""
        ])
    table.align = "l"
    print(env_obj)
    print(table.get_string())
    if return_code:
        raise typer.Exit(code=return_code)


@env_app.command()
def check(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            envvar=envutils.ENV_ENV,
            help="UUID or name of the env."
        )
    ],
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
    detailed: t.Annotated[
        bool,
        typer.Option(
            "--detailed",
            help="Show detailed information."
        )
    ] = False,
) -> None:
    """Check availability of all platforms in environment."""
    env_obj = env_mgr.EnvManager.get(env)
    data = env_obj.check_health()
    available = all(x["available"] for x in data.values())

    if to_json:
        print(json.dumps(data, indent=2))
        if not available:
            raise typer.Exit(code=1)
        return

    def _format_raw(plugin_name: str, el: dict) -> list:
        return [
            el["available"] and YES or NO,
            plugin_name.split("@")[1], el["message"], plugin_name
        ]

    table = prettytable.PrettyTable()
    if detailed:
        table.field_names = ["Available", "Platform", "Message", "Plugin"]
        for plugin_name, r in data.items():
            table.add_row(_format_raw(plugin_name, r))
    else:
        table.field_names = ["Available", "Platform", "Message"]
        for plugin_name, r in data.items():
            table.add_row(_format_raw(plugin_name, r)[:3])

    table.align = "l"
    table.align["available"] = "c"
    table.sortby = "Platform"
    print("%s %s" % (env_obj, available and YES or NO))
    print(table.get_string())
    if not available and detailed:
        for name, p_data in data.items():
            if p_data["available"]:
                continue
            print("-" * 4)
            print("Plugin %s raised exception:" % name)
            print("".join(p_data["traceback"]))

    if not available:
        raise typer.Exit(code=1)


@env_app.command()
def use(
    env: t.Annotated[
        str,
        argutils.ArgumentOrKeyword(
            "--env",
            help="UUID or name of the env."
        )
    ],
    to_json: t.Annotated[
        bool,
        typer.Option(
            "--json",
            help="Format output as JSON."
        )
    ] = False,
) -> None:
    """Set default environment."""
    try:
        env_obj = env_mgr.EnvManager.get(env)
    except exceptions.DBRecordNotFound:
        _print("Can't use non existing environment %s." % env, to_json)
        raise typer.Exit(code=1)
    _use(env_obj.uuid, to_json)
