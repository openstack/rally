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


from rally import db
from rally.openstack.common.fixture import config
from rally.openstack.common import test


class DatabaseFixture(config.Config):
    """Create clean DB before starting test."""
    def setUp(self):
        super(DatabaseFixture, self).setUp()
        db.db_cleanup()
        self.conf.set_default('connection', "sqlite://", group='database')
        db.db_drop()
        db.db_create()


class TestCase(test.BaseTestCase):
    """Test case base class for all unit tests.

    Due to the slowness of DB access, please consider deriving from
    `NoDBTestCase` first.
    """
    USES_DB = True

    def setUp(self):
        super(TestCase, self).setUp()
        if self.USES_DB:
            self.useFixture(DatabaseFixture())


class NoDBTestCase(TestCase):
    """`NoDBTestCase` differs from TestCase in that it doesn't create DB.

    This makes tests run significantly faster. If possible, all new tests
    should derive from this class.
    """
    USES_DB = False
