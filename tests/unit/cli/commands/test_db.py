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

from rally.common import cfg
from rally.common import db
from tests.unit.cli import test


class DBCommandsTestCase(test.CLITestCase):

    # the db commands manage the schema themselves; start from an empty DB
    APPLY_DB_SCHEMA = False

    def test_recreate(self):
        # an empty DB has no schema revision yet ("db revision" prints None)
        self.assertEqual(
            "None", self.invoke(["db", "revision"]).output.strip())

        result = self.invoke(["db", "recreate"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Database deleted successfully", result.output)
        self.assertIn("Database created successfully", result.output)
        # recreate installed the schema -> a real revision now
        self.assertNotEqual(
            "None", self.invoke(["db", "revision"]).output.strip())

    def test_create(self):
        self.assertEqual(
            "None", self.invoke(["db", "revision"]).output.strip())

        result = self.invoke(["db", "create"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Database created successfully", result.output)
        self.assertNotEqual(
            "None", self.invoke(["db", "revision"]).output.strip())

    def test_ensure_create(self):
        # empty DB -> ensure creates it
        result = self.invoke(["db", "ensure"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Database created successfully", result.output)

    def test_ensure_exists(self):
        db.schema.schema_create()

        result = self.invoke(["db", "ensure"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Database already exists, nothing to do", result.output)

    def test_upgrade(self):
        db.schema.schema_create()

        result = self.invoke(["db", "upgrade"])

        self.assertEqual(0, result.exit_code, result.output)
        self.assertIn("Database is already up to date", result.output)

    def test_revision(self):
        db.schema.schema_create()

        result = self.invoke(["db", "revision"])

        self.assertEqual(0, result.exit_code, result.output)
        revision = result.output.strip()
        self.assertTrue(revision)
        self.assertNotEqual("None", revision)

    def test_show(self):
        cfg.CONF.set_default("connection", "http://aaa:bbb@testing.com:888",
                             group="database")
        for args, expected in (
            ([], "http://**:**@testing.com:888"),
            (["--creds"], "http://aaa:bbb@testing.com:888"),
        ):
            with self.subTest(args=args):
                result = self.invoke(["db", "show", *args])
                self.assertEqual(0, result.exit_code, result.output)
                self.assertIn(expected, result.output)
