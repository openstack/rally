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

"""``:pyproject:`` inserts a value from the project's pyproject.toml.

The argument is a dotted path to the value, optionally followed by a filter:

* ``:pyproject:`project.optional-dependencies.mysql``` gives
  ``PyMySQL>=0.9.0``; a list is joined with commas.
* ``:pyproject:`project.requires-python | min``` gives the lowest version a
  specifier allows, for example ``3.11``.
"""

from __future__ import annotations

import pathlib
import tomllib
import typing as t

from docutils import nodes
from packaging import specifiers
from packaging import version

import rally


ROOT = pathlib.Path(rally.__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def min_version(value: str) -> str:
    lower = [
        spec.version
        for spec in specifiers.SpecifierSet(value)
        if spec.operator in (">=", "~=", "==")
    ]
    if not lower:
        raise ValueError(f"{value!r} has no lower bound")
    return max(lower, key=version.Version)


FILTERS: dict[str, t.Callable[[str], str]] = {"min": min_version}


def get_value(text: str, path: pathlib.Path = PYPROJECT) -> str:
    key, _, filter_name = (part.strip() for part in text.partition("|"))
    with path.open("rb") as f:
        value: t.Any = tomllib.load(f)
    for part in key.split("."):
        value = value[part]
    if isinstance(value, list):
        value = ", ".join(value)
    if filter_name:
        value = FILTERS[filter_name](value)
    return str(value)


def pyproject_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: t.Any,
    options: dict | None = None,
    content: list | None = None,
) -> tuple[list, list]:
    try:
        value = get_value(text)
    except (KeyError, ValueError) as e:
        msg = inliner.reporter.error(
            f"Cannot take {text!r} from {PYPROJECT.name}: {e}", line=lineno
        )
        return [inliner.problematic(rawtext, rawtext, msg)], [msg]
    return [nodes.inline("", value)], []


def setup(app: t.Any) -> dict[str, t.Any]:
    app.add_role("pyproject", pyproject_role)
    return {"parallel_read_safe": True}
