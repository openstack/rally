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

import fixtures
from fixtures._fixtures.tempdir import TempDir
import os
from unittest import mock
import uuid

import testtools

from rally.common import cfg
from rally.common import db
from rally import plugins


class TempHomeDir(TempDir):
    """Create a temporary directory and set it as $HOME

    :ivar path: the path of the temporary directory.
    """

    def _setUp(self):
        super(TempHomeDir, self)._setUp()
        self.useFixture(fixtures.EnvironmentVariable("HOME", self.path))


class DatabaseFixture(cfg.fixture.Config):
    """Create clean DB before starting test."""
    def setUp(self):
        super(DatabaseFixture, self).setUp()
        db_url = os.environ.get("RALLY_UNITTEST_DB_URL", "sqlite://")
        db.engine_reset()
        self.conf.set_default("connection", db_url, group="database")
        db.schema.schema_cleanup()
        db.schema.schema_create()


class TestCase(testtools.TestCase):
    """Test case base class for all unit tests."""

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)

        # This is the number of characters shown when two objects do not
        # match for assertDictEqual, assertMultiLineEqual, and
        # assertSequenceEqual. The default is 640 which is too
        # low for comparing most dicts
        self.maxDiff = 10000

    def setUp(self):
        super(TestCase, self).setUp()
        self.addCleanup(mock.patch.stopall)
        plugins.load()
        self.useFixture(TempHomeDir())

    def _test_atomic_action_timer(self, atomic_actions, name, count=1,
                                  parent=[]):

        if parent:
            is_found = False
            for action in atomic_actions:
                if action["name"] == parent[0]:
                    is_found = True
                    self._test_atomic_action_timer(action["children"],
                                                   name, count=count,
                                                   parent=parent[1:])
            if not is_found:
                self.fail("The parent action %s can not be found."
                          % parent[0])
        else:
            actual_count = 0
            for atomic_action in atomic_actions:
                if atomic_action["name"] == name:
                    self.assertIsInstance(atomic_action["started_at"], float)
                    self.assertIsInstance(atomic_action["finished_at"], float)
                    actual_count += 1
            if count != actual_count:
                self.fail("%(count)d count is expected for atomic action"
                          " %(name)s, the actual count"
                          " is %(actual_count)d."
                          % {"name": name, "count": count,
                             "actual_count": actual_count})

    def assertSequenceEqual(self, iterable_1, iterable_2, msg=None):
        self.assertEqual(tuple(iterable_1), tuple(iterable_2), msg)

    _IS_EMPTY_MSG = "Iterable is not empty"

    def assertIsEmpty(self, iterable, msg=None):
        if len(iterable):
            if msg:
                msg = "%s : %s" % (self._IS_EMPTY_MSG, msg)
            else:
                msg = self._IS_EMPTY_MSG
            raise self.failureException(msg)


class DBTestCase(TestCase):
    """Base class for tests which use DB."""

    def setUp(self):
        super(DBTestCase, self).setUp()
        self.useFixture(DatabaseFixture())


def get_test_context(**kwargs):
    kwargs["task"] = {"uuid": str(uuid.uuid4())}
    kwargs["owner_id"] = str(uuid.uuid4())
    return kwargs
