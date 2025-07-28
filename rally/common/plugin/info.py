# Copyright 2015: Mirantis Inc.
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

from __future__ import annotations

import re
import sys
import typing as t

if t.TYPE_CHECKING:
    from rally.common.plugin import plugin

PARAM_OR_RETURNS_REGEX = re.compile(":(?:param|returns)")
RETURNS_REGEX = re.compile(":returns: (?P<doc>.*)", re.S)
PARAM_REGEX = re.compile(r":param (?P<name>[\*\w]+): (?P<doc>.*?)"
                         r"(?:(?=:param)|(?=:return)|(?=:raises)|\Z)", re.S)


def trim(docstring: str) -> str:
    """trim function from PEP-257"""
    if not docstring:
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)

    # Current code/unittests expects a line return at
    # end of multiline docstrings
    # workaround expected behavior from unittests
    if "\n" in docstring:
        trimmed.append("")

    # Return a single string:
    return "\n".join(trimmed)


def reindent(string: str) -> str:
    return "\n".join(line.strip() for line in string.strip().split("\n"))


class _ParamInfo(t.TypedDict):
    """Type for parameter information in docstring parsing."""
    name: str
    doc: str


class _DocstringInfo(t.TypedDict):
    """Type for parsed docstring information."""
    short_description: str
    long_description: str
    params: list[_ParamInfo]
    returns: str


def parse_docstring(docstring: str | None) -> _DocstringInfo:
    """Parse the docstring into its components.

    :returns: a dictionary of form
              {
                  "short_description": ...,
                  "long_description": ...,
                  "params": [{"name": ..., "doc": ...}, ...],
                  "returns": ...
              }
    """

    short_description = long_description = returns = ""
    params: list[_ParamInfo] = []

    if docstring:
        docstring = trim(docstring.lstrip("\n"))

        lines = docstring.split("\n", 1)
        short_description = lines[0]

        if len(lines) > 1:
            long_description = lines[1].strip()

            params_returns_desc = None

            match = PARAM_OR_RETURNS_REGEX.search(long_description)
            if match:
                long_desc_end = match.start()
                params_returns_desc = long_description[long_desc_end:].strip()
                long_description = long_description[:long_desc_end].rstrip()

            if params_returns_desc:
                params = [
                    _ParamInfo(name=name, doc=trim(doc))
                    for name, doc in PARAM_REGEX.findall(params_returns_desc)
                ]

                match = RETURNS_REGEX.search(params_returns_desc)
                if match:
                    returns = reindent(match.group("doc"))

    return {
        "short_description": short_description,
        "long_description": long_description,
        "params": params,
        "returns": returns
    }


class _PluginInfo(t.TypedDict):
    """Type for plugin information returned by get_info method."""
    name: str
    platform: str
    module: str
    title: str
    description: str
    parameters: list[_ParamInfo]
    schema: str | None
    returns: str


class InfoMixin:

    @classmethod
    def _get_doc(cls) -> str | None:
        """Return documentary of class

        By default it returns docstring of class, but it can be overridden
        for example for cases like merging own docstring with parent
        """
        return cls.__doc__

    @classmethod
    def get_info(  # type: ignore[misc]
        cls: type[plugin.Plugin]
    ) -> _PluginInfo:
        doc = parse_docstring(cls._get_doc())

        return {
            "name": cls.get_name(),
            "platform": cls.get_platform(),
            "module": cls.__module__,
            "title": doc["short_description"],
            "description": doc["long_description"],
            "parameters": doc["params"],
            "schema": getattr(cls, "CONFIG_SCHEMA", None),
            "returns": doc["returns"]
        }
