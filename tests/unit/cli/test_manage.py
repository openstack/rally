# Copyright 2013: Mirantis Inc.
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

import sys

import mock

from rally.cli import manage
from tests.unit import fakes
from tests.unit import test


class CmdManageTestCase(test.TestCase):

    @mock.patch("rally.cli.manage.cliutils")
    def test_main(self, mock_cliutils):
        manage.main()
        categories = {"db": manage.DBCommands}
        mock_cliutils.run.assert_called_once_with(sys.argv, categories,
                                                  skip_db_check=True)


class DBCommandsTestCase(test.TestCase):

    def setUp(self):
        super(DBCommandsTestCase, self).setUp()
        self.db_commands = manage.DBCommands()
        self.fake_api = fakes.FakeAPI()

    @mock.patch("rally.cli.manage.envutils")
    @mock.patch("rally.cli.manage.db")
    def test_recreate(self, mock_db, mock_envutils):
        self.db_commands.recreate(self.fake_api)
        db_calls = [mock.call.schema_cleanup(),
                    mock.call.schema_create()]
        self.assertEqual(db_calls, mock_db.mock_calls)
        envutils_calls = [mock.call.clear_env()]
        self.assertEqual(envutils_calls, mock_envutils.mock_calls)

    @mock.patch("rally.cli.manage.db")
    def test_create(self, mock_db):
        self.db_commands.create(self.fake_api)
        calls = [mock.call.schema_create()]
        self.assertEqual(calls, mock_db.mock_calls)

    @mock.patch("rally.cli.manage.db")
    def test_upgrade(self, mock_db):
        self.db_commands.upgrade(self.fake_api)
        calls = [mock.call.schema_upgrade()]
        mock_db.assert_has_calls(calls)

    @mock.patch("rally.cli.manage.db")
    def test_revision(self, mock_db):
        self.db_commands.revision(self.fake_api)
        calls = [mock.call.schema_revision()]
        mock_db.assert_has_calls(calls)
