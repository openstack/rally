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

"""``:package:`` inserts a value from the metadata of the installed rally.

The argument is a metadata field, optionally followed by a filter:

* ``:package:`requires-python | min``` gives the lowest Python version the
  package allows, for example ``3.11``.
* ``:package:`extra mysql``` gives the requirements that the ``mysql`` extra
  adds, for example ``PyMySQL>=0.9.0``; several are joined with commas.
"""

from __future__ import annotations

import importlib.metadata
import typing as t

from docutils import nodes
from packaging import requirements
from packaging import specifiers
from packaging import version


DISTRIBUTION = "rally"


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


def extra_requirements(metadata: t.Any, extra: str) -> str:
    if extra not in (metadata.get_all("Provides-Extra") or []):
        raise ValueError(f"there is no {extra!r} extra")
    found = []
    for line in metadata.get_all("Requires-Dist") or []:
        req = requirements.Requirement(line)
        if req.marker is not None and req.marker.evaluate({"extra": extra}):
            req.marker = None
            found.append(str(req))
    return ", ".join(found)


def get_value(text: str) -> str:
    key, _, filter_name = (part.strip() for part in text.partition("|"))
    metadata = importlib.metadata.metadata(DISTRIBUTION)
    field, _, argument = key.partition(" ")
    if field == "extra":
        value = extra_requirements(metadata, argument.strip())
    elif key in metadata:
        value = metadata[key]
    else:
        raise ValueError(f"there is no {key!r} field")
    if filter_name:
        value = FILTERS[filter_name](value)
    return value


def package_role(
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
            f"Cannot take {text!r} from the {DISTRIBUTION} metadata: {e}",
            line=lineno,
        )
        return [inliner.problematic(rawtext, rawtext, msg)], [msg]
    return [nodes.inline("", value)], []


def setup(app: t.Any) -> dict[str, t.Any]:
    app.add_role("package", package_role)
    return {"parallel_read_safe": True}
