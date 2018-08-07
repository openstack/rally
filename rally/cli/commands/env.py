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

import json
import os
import prettytable
import traceback

from rally.cli import cliutils
from rally.cli import envutils
from rally.common import fileutils
from rally.common import yamlutils as yaml
from rally.env import env_mgr
from rally import exceptions


YES = u":-)"
NO = u":-("


def _print(msg, silent=False):
    if not silent:
        print(msg)


# TODO(boris-42): Wrap all methods to catch EnvManager Exceptions
class EnvCommands(object):
    """Set of commands that allow you to manage envs."""

    @cliutils.args("--name", "-n", type=str, required=True,
                   help="Name of the env.")
    @cliutils.args("--description", "-d", type=str, required=False,
                   help="Env description")
    @cliutils.args("--extras", "-e", type=str, required=False,
                   help="JSON or YAML dict with custom non validate info.")
    @cliutils.args("--from-sysenv", action="store_true", dest="from_sysenv",
                   help="Iterate over all available platforms and check system"
                        " environment for credentials.")
    @cliutils.args("--spec", "-s", type=str, required=False,
                   metavar="<path>", help="Path to env spec.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.args("--no-use", action="store_false", dest="do_use",
                   help="Don't set new env as default for future operations.")
    def create(self, api, name, description=None, extras=None,
               spec=None, from_sysenv=False, to_json=False, do_use=True):
        """Create new environment."""

        if spec is not None and from_sysenv:
            print("Arguments '--spec' and '--from-sysenv' cannot be used "
                  "together, use only one of them.")
            return 1
        spec = spec or {}
        if spec:
            with open(os.path.expanduser(spec), "rb") as f:
                spec = yaml.safe_load(f.read())
        if extras:
            extras = yaml.safe_load(extras)

        if from_sysenv:
            result = env_mgr.EnvManager.create_spec_from_sys_environ()
            spec = result["spec"]
            _print("Your system environment includes specifications of "
                   "%s platform(s)." % len(spec), to_json)
            _print("Discovery information:", to_json)
            for p_name, p_result in result["discovery_details"].items():
                _print("\t - %s : %s." % (p_name, p_result["message"]),
                       to_json)

                if "traceback" in p_result:
                    _print("".join(p_result["traceback"]), to_json)
        try:
            env = env_mgr.EnvManager.create(
                name, spec, description=description, extras=extras)
        except exceptions.ManagerInvalidSpec as e:
            _print("Env spec has wrong format:", to_json)
            _print(json.dumps(e.kwargs["spec"], indent=2), to_json)
            for err in e.kwargs["errors"]:
                _print(err, to_json)
            return 1
        except Exception:
            _print("Something went wrong during env creation:", to_json)
            _print(traceback.print_exc(), to_json)
            return 1

        if do_use:
            self._use(env.uuid, to_json)
        self._show(env.data, to_json=to_json, only_spec=False)
        return 0

    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @envutils.with_default_env()
    def cleanup(self, api, env=None, to_json=False):
        """Perform disaster cleanup for specified environment.

        Cases when Rally can leave undeleted resources after performing
        workload:

        - Rally execution was interrupted and cleanup was not performed
        - The environment or a particular platform became unreachable which
          fail Rally execution of cleanup
        """
        env = env_mgr.EnvManager.get(env)
        _print("Cleaning up resources for %s" % env, to_json)
        result = env.cleanup()

        if to_json:
            print(json.dumps(result, indent=2))
            return int(any([p["errors"] for p in result.values()]))

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

        return return_code

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @cliutils.args("--skip-cleanup", action="store_true", dest="skip_cleanup",
                   help="Do not perform platforms cleanup before destroy.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.args("--detailed", action="store_true", dest="detailed",
                   help="Show detailed information.")
    @envutils.with_default_env()
    def destroy(self, api, env=None, skip_cleanup=False, to_json=False,
                detailed=False):
        """Destroy existing environment."""
        env = env_mgr.EnvManager.get(env)
        _print("Destroying %s" % env, to_json)
        result = env.destroy(skip_cleanup)
        return_code = int(result["destroy_info"]["skipped"])

        if result["destroy_info"]["skipped"]:
            _print("%s Failed to destroy env %s: %s"
                   % (NO, env, result["destroy_info"]["message"]), to_json)
        else:
            _print("%s Successfully destroyed env %s" % (YES, env), to_json)

        if detailed or to_json:
            print(json.dumps(result, indent=2))

        return return_code

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @cliutils.args("--force", action="store_true", dest="force",
                   help="Delete DB records even if env is not destroyed.")
    @envutils.with_default_env()
    def delete(self, api, env=None, force=False):
        """Deletes all records related to the environment from db."""
        env_mgr.EnvManager.get(env).delete(force=force)
        # TODO(boris-42): clear env variables if default one is deleted

    MSG_NO_ENVS = ("There are no environments. To create a new environment, "
                   "use command bellow to create one:\nrally env create")

    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.suppress_warnings
    def list(self, api, to_json=False):
        """List existing environments."""
        envs = env_mgr.EnvManager.list()
        if to_json:
            print(json.dumps([env.cached_data for env in envs], indent=2))
        elif not envs:
            print(self.MSG_NO_ENVS)
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

    def _show(self, env_data, to_json, only_spec):
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

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.args("--only-spec", action="store_true", dest="only_spec",
                   help="Print only a spec for the environment.")
    @cliutils.suppress_warnings
    @envutils.with_default_env()
    def show(self, api, env=None, to_json=False, only_spec=False):
        """Show base information about the environment record."""
        env_data = env_mgr.EnvManager.get(env).data
        self._show(env_data, to_json=to_json, only_spec=only_spec)

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @envutils.with_default_env()
    def info(self, api, env=None, to_json=False):
        """Retrieve and show environment information."""
        env = env_mgr.EnvManager.get(env)
        env_info = env.get_info()
        return_code = int(any(v.get("error") for v in env_info.values()))

        if to_json:
            print(json.dumps(env_info, indent=2))
            return return_code

        table = prettytable.PrettyTable()
        table.field_names = ["platform", "info", "error"]
        for platform, data in env_info.items():
            table.add_row([
                platform, json.dumps(data["info"], indent=2),
                data.get("error") or ""
            ])
        table.align = "l"
        print(env)
        print(table.get_string())
        return return_code

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of the env.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    @cliutils.args("--detailed", action="store_true", dest="detailed",
                   help="Show detailed information.")
    @envutils.with_default_env()
    def check(self, api, env=None, to_json=False, detailed=False):
        """Check availability of all platforms in environment."""
        env = env_mgr.EnvManager.get(env)
        data = env.check_health()
        available = all(x["available"] for x in data.values())

        if to_json:
            print(json.dumps(data, indent=2))
            return not available

        def _format_raw(plugin_name, el):
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
        print("%s %s" % (env, available and YES or NO))
        print(table.get_string())
        if not available and detailed:
            for name, p_data in data.items():
                if p_data["available"]:
                    continue
                print("-" * 4)
                print("Plugin %s raised exception:" % name)
                print("".join(p_data["traceback"]))

        return not available

    @cliutils.args("--env", dest="env", type=str,
                   metavar="<uuid>", required=False,
                   help="UUID or name of a env.")
    @cliutils.args("--json", action="store_true", dest="to_json",
                   help="Format output as JSON.")
    def use(self, api, env, to_json=False):
        """Set default environment."""
        try:
            env = env_mgr.EnvManager.get(env)
        except exceptions.DBRecordNotFound:
            _print("Can't use non existing environment %s." % env, to_json)
            return 1
        self._use(env.uuid, to_json)

    def _use(self, env_uuid, to_json):
        _print("Using environment: %s" % env_uuid, to_json)
        fileutils.update_globals_file(envutils.ENV_ENV, env_uuid)
