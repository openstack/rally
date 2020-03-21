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

from unittest import mock

from rally.cli.commands import db
from tests.unit import fakes
from tests.unit import test


class DBCommandsTestCase(test.TestCase):

    def setUp(self):
        super(DBCommandsTestCase, self).setUp()
        self.db_commands = db.DBCommands()
        self.fake_api = fakes.FakeAPI()

    @mock.patch("rally.cli.commands.db.envutils")
    @mock.patch("rally.cli.commands.db.db.schema")
    def test_recreate(self, mock_db_schema, mock_envutils):
        self.db_commands.recreate(self.fake_api)
        db_calls = [mock.call.schema_cleanup(),
                    mock.call.schema_create()]
        self.assertEqual(db_calls, mock_db_schema.mock_calls)
        envutils_calls = [mock.call.clear_env()]
        self.assertEqual(envutils_calls, mock_envutils.mock_calls)

    @mock.patch("rally.cli.commands.db.db.schema")
    def test_create(self, mock_db_schema):
        self.db_commands.create(self.fake_api)
        calls = [mock.call.schema_create()]
        self.assertEqual(calls, mock_db_schema.mock_calls)

    @mock.patch("rally.cli.commands.db.db.schema")
    def test_ensure_create(self, mock_db_schema):
        mock_db_schema.schema_revision.return_value = None
        self.db_commands.ensure(self.fake_api)
        calls = [mock.call.schema_revision(),
                 mock.call.schema_create()]
        self.assertEqual(calls, mock_db_schema.mock_calls)

    @mock.patch("rally.cli.commands.db.db.schema")
    def test_ensure_exists(self, mock_db_schema):
        mock_db_schema.schema_revision.return_value = "revision"
        self.db_commands.ensure(self.fake_api)
        calls = [mock.call.schema_revision()]
        self.assertEqual(calls, mock_db_schema.mock_calls)

    @mock.patch("rally.cli.commands.db.db.schema")
    def test_upgrade(self, mock_db_schema):
        self.db_commands.upgrade(self.fake_api)
        calls = [mock.call.schema_upgrade()]
        mock_db_schema.assert_has_calls(calls)

    @mock.patch("rally.cli.commands.db.db.schema")
    def test_revision(self, mock_db_schema):
        self.db_commands.revision(self.fake_api)
        calls = [mock.call.schema_revision()]
        mock_db_schema.assert_has_calls(calls)

    @mock.patch("rally.cli.commands.db.print")
    @mock.patch("rally.cli.commands.db.cfg.CONF.database")
    def test_show(self, mock_conf_database, mock_print):
        mock_conf_database.connection = "http://aaa:bbb@testing.com:888"
        self.db_commands.show(self.fake_api)
        mock_print.assert_called_once_with("http://**:**@testing.com:888")
        mock_print.reset_mock()
        self.db_commands.show(self.fake_api, show_creds=True)
        mock_print.assert_called_once_with("http://aaa:bbb@testing.com:888")
