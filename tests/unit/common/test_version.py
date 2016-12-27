# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from rally.common import version
from tests.unit import test


class ModuleTestCase(test.TestCase):

    VERSION_REGEX = "^\d+\.\d+\.\d+(~dev\d+)?$"

    def test_version_info(self):
        version_str = version.version_info.semantic_version().debian_string()
        self.assertRegexpMatches(version_str, self.VERSION_REGEX)

    @mock.patch("rally.common.version.version_info")
    def test_version_string(self, mock_version_info):
        mock_sv = mock.Mock()
        mock_sv.debian_string.return_value = "foo_version"
        mock_version_info.semantic_version.return_value = mock_sv
        self.assertEqual("foo_version", version.version_string())

    @mock.patch("rally.common.db.api.schema_revision", return_value="foo")
    def test_database_revision(self, mock_schema_revision):
        self.assertEqual("foo", version.database_revision())
        mock_schema_revision.assert_called_once_with(detailed=True)
