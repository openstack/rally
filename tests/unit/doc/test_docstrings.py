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

from docutils import nodes

from rally.common.plugin import plugin
from rally.common import validation
from rally import plugins
from rally.task import scenario
from tests.unit.doc import utils
from tests.unit import test


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

    def _iterate_parsed_rst(self, plugin_name, items, msg_buffer):
        for item in items:
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
            elif item.children:
                self._iterate_parsed_rst(plugin_name, item.children,
                                         msg_buffer)

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
                parsed_docstring = utils.parse_rst(doc_info["description"])
                self._iterate_parsed_rst(plg_cls.get_name(),
                                         parsed_docstring,
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

    def test_plugin_bases_have_docstrigs(self):
        plugin_bases = set()
        msg_buffer = []
        for plg_cls in plugin.Plugin.get_all(allow_hidden=True):
            plugin_bases.add(plg_cls._get_base())
        for base in plugin_bases:
            name = "%s.%s" % (base.__module__, base.__name__)
            try:
                docstring = base._get_doc()
            except Exception:
                docstring = base.__doc__

            print(name)
            parsed_docstring = utils.parse_rst(docstring)
            self._iterate_parsed_rst(name,
                                     parsed_docstring,
                                     msg_buffer)

        if msg_buffer:
            self.fail("\n%s" % "\n===============\n".join(msg_buffer))
