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


def parse_text(text: str, *, source: str = "<generated rst>") -> list:
    """Parse reStructuredText into docutils nodes.

    :param text: the reStructuredText to parse
    :param source: the name that warnings about the text are reported with,
        followed by the line number inside the text
    """
    parser = rst.Parser()
    settings = frontend.OptionParser(
        components=(rst.Parser,)
    ).get_default_values()
    document = utils.new_document(source, settings)
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


def make_definition(
    term: str,
    ref: str,
    descriptions: list,
    qualifiers: list[str] | None = None,
) -> t.Any:
    """Constructs definition with reference to it.

    ``qualifiers`` are rendered as ``term (a, b)`` next to the term, matching
    how the plugin reference shows a parameter's type and requiredness.
    """
    # docutils turns the target name of ``.. _<ref>:`` into an id with
    # make_id(), while the ``__ #<ref>`` URI is kept verbatim, so the ref is
    # normalized the same way (e.g. an uppercase UUID metavar, or a leading
    # "-" of a command without a category) to not link to a missing anchor
    ref = nodes.make_id(ref)
    suffix = f" ({', '.join(qualifiers)})" if qualifiers else ""
    # render the term (e.g. CLI flags like ``--uuid``) as an inline literal:
    # emphasis would let Sphinx's smartquotes mangle ``--`` into an en-dash
    # the anonymous target is indented into the list item on purpose: docutils
    # pairs anonymous references with targets in document order, and the
    # descriptions below may carry their own pair (e.g. the "use"-command
    # hint).  Keeping each target next to its reference stops them swapping.
    definition = parse_text(
        f".. _{ref}:\n\n* ``{term}``{suffix} [ref__]\n\n  __ #{ref}"
    )
    # nest the descriptions inside the list item, so they are indented under
    # the flag they describe.  Appending them to ``definition`` would make
    # them siblings of the whole bullet list instead.
    container: t.Any = definition
    for node in definition:
        if isinstance(node, nodes.bullet_list) and len(node):
            container = node[0]
            break

    for descr in descriptions:
        if descr:
            if isinstance(descr, str):
                if descr[0] not in string.ascii_uppercase:
                    # .capitalize() removes existing caps
                    descr = descr[0].upper() + descr[1:]
                descr = paragraph(descr)
            container.append(descr)
    return definition
