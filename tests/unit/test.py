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

import os
import uuid

import mock
from oslo_config import fixture
from oslotest import base
from oslotest import mockpatch

from rally.common import db
from rally import plugins
from tests.unit import fakes


class DatabaseFixture(fixture.Config):
    """Create clean DB before starting test."""
    def setUp(self):
        super(DatabaseFixture, self).setUp()
        db_url = os.environ.get("RALLY_UNITTEST_DB_URL", "sqlite://")
        db.db_cleanup()
        self.conf.set_default("connection", db_url, group="database")
        db.db_drop()
        db.db_create()


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.addCleanup(mock.patch.stopall)
        plugins.load()

    def _test_atomic_action_timer(self, atomic_actions, name):
        action_duration = atomic_actions.get(name)
        self.assertIsNotNone(action_duration)
        self.assertIsInstance(action_duration, float)

    def assertSequenceEqual(self, iterable_1, iterable_2):
        self.assertEqual(tuple(iterable_1), tuple(iterable_2))


class DBTestCase(TestCase):
    """Base class for tests which use DB."""

    def setUp(self):
        super(DBTestCase, self).setUp()
        self.useFixture(DatabaseFixture())


# TODO(boris-42): This should be moved to test.plugins.test module
#                 or similar

class ScenarioTestCase(TestCase):
    """Base class for Scenario tests using mocked self.clients."""
    benchmark_utils = "rally.task.utils"
    patch_benchmark_utils = True

    def client_factory(self, client_type, version=None, admin=False):
        """Create a new client object."""
        return mock.MagicMock(client_type=client_type,
                              version=version,
                              admin=admin)

    def clients(self, client_type, version=None, admin=False):
        """Get a mocked client."""
        key = (client_type, version, admin)
        if key not in self._clients:
            self._clients[key] = self.client_factory(client_type,
                                                     version=version,
                                                     admin=admin)
        return self._clients[key]

    def admin_clients(self, client_type, version=None):
        """Get a mocked admin client."""
        return self.clients(client_type, version=version, admin=True)

    def client_created(self, client_type, version=None, admin=False):
        """Determine if a client has been created.

        This can be used to see if a scenario calls
        'self.clients("foo")', without checking to see what was done
        with the client object returned by that call.
        """
        key = (client_type, version, admin)
        return key in self._clients

    def setUp(self):
        super(ScenarioTestCase, self).setUp()
        if self.patch_benchmark_utils:
            self.mock_resource_is = mockpatch.Patch(
                self.benchmark_utils + ".resource_is")
            self.mock_get_from_manager = mockpatch.Patch(
                self.benchmark_utils + ".get_from_manager")
            self.mock_wait_for = mockpatch.Patch(
                self.benchmark_utils + ".wait_for")
            self.mock_wait_for_delete = mockpatch.Patch(
                self.benchmark_utils + ".wait_for_delete")
            self.useFixture(self.mock_resource_is)
            self.useFixture(self.mock_get_from_manager)
            self.useFixture(self.mock_wait_for)
            self.useFixture(self.mock_wait_for_delete)

        self.mock_sleep = mockpatch.Patch("time.sleep")
        self.useFixture(self.mock_sleep)

        self._clients = {}
        base_path = "rally.plugins.openstack"
        self._client_mocks = [
            mock.patch(
                "%s.scenario.OpenStackScenario.clients" % base_path,
                mock.Mock(side_effect=self.clients)),
            mock.patch(
                "%s.scenario.OpenStackScenario.admin_clients" % base_path,
                mock.Mock(side_effect=self.admin_clients))
        ]
        for patcher in self._client_mocks:
            patcher.start()

        self.context = get_test_context()

    def tearDown(self):
        for patcher in self._client_mocks:
            patcher.stop()
        super(ScenarioTestCase, self).tearDown()


class FakeClientsScenarioTestCase(ScenarioTestCase):
    """Base class for Scenario tests using fake (not mocked) self.clients."""

    def client_factory(self, client_type, version=None, admin=False):
        return getattr(self._fake_clients, client_type)()

    def setUp(self):
        super(FakeClientsScenarioTestCase, self).setUp()
        self._fake_clients = fakes.FakeClients()


def get_test_context():
    return {
        "task": {
            "uuid": str(uuid.uuid4())
        }
    }
