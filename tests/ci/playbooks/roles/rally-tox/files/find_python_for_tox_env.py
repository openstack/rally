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

import argparse
import configparser
import re


PY_FACTORS_RE = re.compile("^(?!py$)(py|pypy|jython)([2-9][0-9]?[0-9]?)?$")


def _parse_env_name(env_name):
    for factor in env_name.split("-"):
        # copy-pasted from tox codebase with custom extra check
        # https://github.com/tox-dev/tox/blob/6b76e18fcaa7c9610b642555bcb94aab1d37f2b3/src/tox/config/__init__.py#L658-L669
        match = PY_FACTORS_RE.match(factor)
        if match:
            base_exe = {"py": "python"}.get(match.group(1), match.group(1))

            if base_exe != "python":
                raise ValueError("We do not support '%s' interpreter yet."
                                 % base_exe)
            version_s = match.group(2)
            if not version_s:
                version_info = ()
            elif len(version_s) == 1:
                version_info = (version_s,)
            else:
                version_info = (version_s[0], version_s[1:])
            implied_version = ".".join(version_info)
            implied_python = "{}{}".format(base_exe, implied_version)
            return implied_python


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tox-cfg", metavar="<path>", type=str, required=True,
        help="A path to tox.ini file to parse."
    )
    parser.add_argument(
        "--tox-env", metavar="<env-name>", type=str, required=True,
        help="Tox env name."
    )
    parser.add_argument(
        "--default-python3-version", metavar="<python-interpreter>",
        type=str, required=False, default="python3.10",
        help="Default python3 interpreter to use for 'python3' case."
    )
    args = parser.parse_args()

    tox_cfg = configparser.ConfigParser()
    tox_cfg.read(args.tox_cfg)

    python_version = None

    # check python version specific to target tox env
    env_section = "testenv:%s" % args.tox_env
    if env_section in tox_cfg:
        python_version = tox_cfg[env_section].get("basepython")

    # try to determine python version based on env name like tox does
    if python_version is None:
        python_version = _parse_env_name(args.tox_env)

    # check python version that is configured for all tox envs as default
    if python_version is None:
        python_version = tox_cfg["testenv"].get("basepython", "python3")

    if python_version == "python3":
        python_version = args.default_python3_version
    print(python_version)


if __name__ == "__main__":
    main()
