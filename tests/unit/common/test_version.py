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

import importlib
from unittest import mock

from rally.common import version
from tests.unit import test


class ModuleTestCase(test.TestCase):

    VERSION_REGEX = r"^\d+\.\d+\.\d+(\.dev\d+)?$"

    def test_version_info(self):
        version_str = version.version_string()
        self.assertRegex(version_str, self.VERSION_REGEX)
        self.assertNotEqual("0.0.0", version_str)

        self.assertEqual(
            version.__version_tuple__,
            version.version_info.semantic_version().version_tuple()
        )

    @mock.patch("setuptools_scm.get_version")
    @mock.patch("importlib.metadata.version")
    def test_version_string(self, mock_version, mock_get_version):
        self.addCleanup(lambda: importlib.reload(version))

        mock_version.return_value = "foo_version"
        mock_get_version.return_value = "bar_version"

        # reload module, so it can rediscover version
        importlib.reload(version)
        # ensure that we reload version after the test
        self.addCleanup(lambda: importlib.reload(version))

        self.assertEqual("foo_version", version.version_string())
        self.assertEqual("foo_version", version.__version__)

        mock_version.assert_called_once_with("rally")
        self.assertFalse(mock_get_version.called)

        # check fallback
        mock_version.reset_mock()
        mock_version.side_effect = Exception("oops")

        importlib.reload(version)
        self.assertEqual("bar_version", version.__version__)
        mock_version.assert_called_once_with("rally")
        mock_get_version.assert_called_once_with()

        # check fallback 2
        mock_version.reset_mock()
        mock_get_version.reset_mock()
        mock_get_version.side_effect = Exception("oops2")

        importlib.reload(version)
        self.assertEqual("0.0.0", version.__version__)
        mock_version.assert_called_once_with("rally")
        mock_get_version.assert_called_once_with()

    @mock.patch("rally.common.db.schema.schema_revision", return_value="foo")
    def test_database_revision(self, mock_schema_revision):
        self.assertEqual("foo", version.database_revision())
        mock_schema_revision.assert_called_once_with(detailed=True)
