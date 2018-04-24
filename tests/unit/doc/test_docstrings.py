# Copyright 2014: Mirantis Inc.
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

from docutils import frontend
from docutils import nodes
from docutils.parsers import rst
from docutils import utils

from rally.common.plugin import plugin
from rally.common import validation
from rally import plugins
from rally.task import scenario
from tests.unit import test


def _parse_rst(text):
    parser = rst.Parser()
    settings = frontend.OptionParser(
        components=(rst.Parser,)).get_default_values()
    document = utils.new_document(text, settings)
    parser.parse(text, document)
    return document.children


class DocstringsTestCase(test.TestCase):

    def setUp(self):
        super(DocstringsTestCase, self).setUp()
        plugins.load()

    def _validate_code_block(self, plg_cls, code_block):
        ignored_params = ["self", "scenario_obj"]
        params_count = code_block.co_argcount
        params = code_block.co_varnames[:params_count]
        param_data = plg_cls.get_info()["parameters"]
        documented_params = [p["name"] for p in param_data]
        result = []
        for param in params:
            if param not in ignored_params:
                if param not in documented_params:
                    msg = ("Class: %(class)s Docstring for "
                           "%(scenario)s should"
                           " describe the '%(param)s' parameter"
                           " in the :param <name>: clause."
                           % {"class": plg_cls.__name__,
                              "scenario": plg_cls.get_name(),
                              "param": param})
                    result.append(msg)
        return result

    # the list with plugins names which use rst definitions in their docstrings
    _HAS_VALID_DEFINITIONS = []

    def _validate_rst(self, plugin_name, text, msg_buffer):
        parsed_docstring = _parse_rst(text)
        for item in parsed_docstring:
            if (isinstance(item, nodes.definition_list)
                    and plugin_name not in self._HAS_VALID_DEFINITIONS):
                msg_buffer.append("Plugin %s has a docstring with invalid "
                                  "format. Re-check intend and required empty "
                                  "lines between the list title and list "
                                  "items." % plugin_name)
            elif isinstance(item, nodes.system_message):
                msg_buffer.append(
                    "A warning is caught while parsing docstring of '%s' "
                    "plugin: %s" % (plugin_name, item.astext()))

    def _check_docstrings(self, msg_buffer):
        for plg_cls in plugin.Plugin.get_all():
            if not plg_cls.__module__.startswith("rally."):
                continue
            name = "%s (%s.%s)" % (plg_cls.get_name(),
                                   plg_cls.__module__,
                                   plg_cls.__name__)
            doc_info = plg_cls.get_info()
            if not doc_info["title"]:
                msg_buffer.append("Plugin '%s' should have a docstring."
                                  % name)
            if doc_info["title"].startswith("Test"):
                msg_buffer.append("One-line description for %s"
                                  " should be declarative and not"
                                  " start with 'Test(s) ...'"
                                  % name)

            # NOTE(andreykurilin): I never saw any real usage of
            #   reStructuredText definitions in our docstrings. In most cases,
            #   "definitions" means that there is an issue with intends or
            #   missed empty line before the list title and list items.
            if doc_info["description"]:
                self._validate_rst(plg_cls.get_name(),
                                   doc_info["description"],
                                   msg_buffer)

    def _check_described_params(self, msg_buffer):
        for plg_cls in plugin.Plugin.get_all():
            msg = []
            if hasattr(plg_cls, "run") and issubclass(
                    plg_cls, scenario.Scenario):
                msg = self._validate_code_block(plg_cls,
                                                plg_cls.run.__code__)
            elif hasattr(plg_cls, "validate") and issubclass(
                    plg_cls, validation.Validator):
                msg = self._validate_code_block(plg_cls,
                                                plg_cls.__init__.__code__)
            msg_buffer.extend(msg) if len(msg) else None

    def test_all_plugins_have_docstrings(self):
        msg_buffer = []
        self._check_docstrings(msg_buffer)

        self._check_described_params(msg_buffer)
        if msg_buffer:
            self.fail("\n%s" % "\n===============\n".join(msg_buffer))
