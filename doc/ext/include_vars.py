# Copyright 2017: Mirantis Inc.
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

from docutils import nodes
import json

from oslo_utils import importutils


def include_var(name, rawtext, text, lineno, inliner, options=None,
                content=None):
    """include variable

    :param name: The local name of the interpreted role, the role name
                 actually used in the document.
    :param rawtext: A string containing the enitre interpreted text input,
                    including the role and markup. Return it as a problematic
                    node linked to a system message if a problem is
                    encountered.
    :param text: The interpreted text content.
    :param lineno: The line number where the interpreted text begins.
    :param inliner: The docutils.parsers.rst.states.Inliner object that
                    called include_var. It contains the several attributes
                    useful for error reporting and document tree access.
    :param options: A dictionary of directive options for customization
                    (from the 'role' directive), to be interpreted by the
                    role function. Used for additional attributes for the
                    generated elements and other functionality.
    :param content: A list of strings, the directive content for
                    customization (from the 'role' directive). To be
                    interpreted by the role function.
    :return:
    """
    obj = importutils.import_class(text)
    if isinstance(obj, (tuple, list)):
        obj = ", ".join(obj)
    elif isinstance(obj, dict):
        obj = json.dumps(dict, indent=4)
    else:
        obj = str(obj)
    return [nodes.Text(obj)], []


def setup(app):
    app.add_role("include-var", include_var)
