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

"""
Docutils is awful library. Let's apply some hacks and aliases to simplify usage
"""

from __future__ import annotations

import string
import typing as t

from docutils import frontend
from docutils import nodes
from docutils import utils
from docutils.parsers import rst


def parse_text(text: str) -> list:
    parser = rst.Parser()
    settings = frontend.OptionParser(
        components=(rst.Parser,)
    ).get_default_values()
    document = utils.new_document(text, settings)
    try:
        parser.parse(text, document)
    except Exception as e:
        print(f"WARNING: {e}")
        return []
    return document.children


paragraph = lambda text: parse_text(text)[0]
note = lambda msg: nodes.note("", paragraph(msg))
hint = lambda msg: nodes.hint("", *parse_text(msg))
warning = lambda msg: nodes.warning("", paragraph(msg))
category = lambda title: parse_text("%s\n%s" % (title, "-" * len(title)))[0]
subcategory = lambda title: parse_text("%s\n%s" % (title, "~" * len(title)))[0]
section = lambda title: parse_text("%s\n%s" % (title, '"' * len(title)))[0]


def make_definition(term: str, ref: str, descriptions: list) -> t.Any:
    """Constructs definition with reference to it."""
    ref = ref.replace("_", "-").replace(" ", "-")
    # render the term (e.g. CLI flags like ``--uuid``) as an inline literal:
    # emphasis would let Sphinx's smartquotes mangle ``--`` into an en-dash
    definition = parse_text(
        ".. _%(ref)s:\n\n* ``%(term)s`` [ref__]\n\n__ #%(ref)s"
        % {"ref": ref, "term": term}
    )
    for descr in descriptions:
        if descr:
            if isinstance(descr, str):
                if descr[0] not in string.ascii_uppercase:
                    descr = descr.capitalize()
                descr = paragraph("  %s" % descr)
            definition.append(descr)
    return definition


def make_definitions(
    title: str,
    ref_prefix: str,
    terms: list[tuple[str, str, list[str]]],
    descriptions: list | None = None,
) -> list:
    """Constructs a list of definitions with reference to them."""
    raw_text = [f"**{title}**:"]
    if descriptions:
        for descr in descriptions:
            raw_text.append(descr)

    for term, ref, definitions in terms:
        ref = (
            f"{ref_prefix}{ref}".lower()
            .replace(".", "-")
            .replace("_", "-")
            .replace(" ", "-")
        )
        raw_text.append(f".. _{ref}:")
        raw_text.append(f"* *{term}* [ref__]")

        for d in definitions:
            d = d.strip() if d else None
            if d:
                if d[0] not in string.ascii_uppercase:
                    # .capitalize() removes existing caps
                    d = d[0].upper() + d[1:]
                d = "\n  ".join(d.split("\n"))
                raw_text.append(f"  {d}")

        raw_text.append(f"__ #{ref}")

    return parse_text("\n\n".join(raw_text) + "\n")
