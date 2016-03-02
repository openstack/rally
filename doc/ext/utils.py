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

from docutils import frontend
from docutils import nodes
from docutils import utils
from docutils.parsers import rst

import six


def parse_text(text):
    parser = rst.Parser()
    settings = frontend.OptionParser(components=(rst.Parser,)).get_default_values()
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    return document.children

paragraph = lambda text: parse_text(text)[0]
note = lambda msg: nodes.note("", paragraph(msg))
hint = lambda msg: nodes.hint("", *parse_text(msg))
warning = lambda msg: nodes.warning("", paragraph(msg))
category = lambda title: parse_text("%s\n%s" % (title, "-" * len(title)))[0]
subcategory = lambda title: parse_text("%s\n%s" % (title, "~" * len(title)))[0]


def make_definition(term, ref, descriptions):
    """Constructs definition with reference to it"""
    ref = ref.replace("_", "-").replace(" ", "-")
    definition = parse_text(
            ".. _%(ref)s:\n\n*%(term)s* (ref__)\n\n__ #%(ref)s" %
            {"ref": ref, "term": term})
    for descr in descriptions:
        if isinstance(descr, (six.text_type, six.binary_type)):
            descr = paragraph("  %s" % descr)
        definition.append(descr)
    return definition
