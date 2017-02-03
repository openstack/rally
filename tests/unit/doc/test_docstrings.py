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

from rally import plugins
from rally.common.plugin import discover
from rally.common.plugin import info
from rally.common.plugin import plugin
from rally.deployment import engine
from rally.deployment.serverprovider import provider
from rally.task import sla
from tests.unit import test

EXCEPTIONS_DOCSTR = "missed_docstrings.txt"
EXCEPTIONS_FORMAT = "wrong_format.txt"


class DocstringsTestCase(test.TestCase):


    def setUp(self):
        super(DocstringsTestCase, self).setUp()
        plugins.load()

        self.exceptions = self._open_file(
            EXCEPTIONS_DOCSTR) + self._open_file(EXCEPTIONS_FORMAT)

    def _open_file(self, filename):
        with open("./tests/unit/doc/%s" % filename) as file:
            return (file.read().lower().split())

    def _check_docstrings(self, msg_buffer):
        for plg_cls in plugin.Plugin.get_all():
            if plg_cls.__module__.startswith("rally."):
                if plg_cls.get_name().lower() not in self.exceptions:
                    doc = info.parse_docstring(plg_cls.__doc__)
                    short_description = doc["short_description"]
                    if short_description.startswith("Test"):
                        msg_buffer.append("One-line description for %s"
                                          " should be declarative and not"
                                          " start with 'Test(s) ...'"
                                          % plg_cls.__name__)
                    if not plg_cls.get_info()["title"]:
                        msg = ("Class '{}' should have a docstring.")
                        inst_name = plg_cls.__name__
                        msg_buffer.append(msg.format(inst_name))

    def _check_described_params(self, msg_buffer):
        for plg_cls in plugin.Plugin.get_all():
            if plg_cls.get_name().lower() not in self.exceptions:
                ignored_params = ["self", "scenario_obj"]
                if hasattr(plg_cls, "run"):
                    code_block = plg_cls.run.__code__
                    params_count = code_block.co_argcount
                    params = code_block.co_varnames[:params_count]
                    param_data = plg_cls.get_info()["parameters"]
                    documented_params = [p["name"] for p in param_data]
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
                                msg_buffer.append(msg)

    def test_all_plugins_have_docstrings(self):

        msg_buffer = []
        self._check_docstrings(msg_buffer)
        if msg_buffer:
            self.fail("\n%s" % "\n".join(msg_buffer))

        msg_buffer = []
        self._check_described_params(msg_buffer)
        if msg_buffer:
            self.fail("\n%s" % "\n".join(msg_buffer))
