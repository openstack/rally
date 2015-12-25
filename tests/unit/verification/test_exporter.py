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

from rally.common.plugin import plugin
from rally.verification import exporter
from tests.unit import test


@plugin.configure(name="test_verify_exporter")
class TestExporter(exporter.VerifyExporter):

    def export(self, uuid, connection_string):
        pass


class ExporterTestCase(test.TestCase):

    def test_task_export(self):
        self.assertRaises(TypeError, exporter.VerifyExporter)

    def test_task_export_instantiate(self):
        TestExporter()
