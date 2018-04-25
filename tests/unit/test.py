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
import uuid

import mock
import testtools

from rally.common import cfg
from rally.common import db
from rally import plugins
from tests.unit import fakes


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


# TODO(boris-42): This should be moved to test.plugins.test module
#                 or similar

class ScenarioTestCase(TestCase):
    """Base class for Scenario tests using mocked self.clients."""
    task_utils = "rally.task.utils"
    patch_task_utils = True

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

    def get_client_mocks(self):
        base_path = "rally.plugins.openstack"

        return [
            mock.patch(
                "%s.scenario.OpenStackScenario.clients" % base_path,
                mock.Mock(side_effect=self.clients)),
            mock.patch(
                "%s.scenario.OpenStackScenario.admin_clients" % base_path,
                mock.Mock(side_effect=self.admin_clients))
        ]

    def get_test_context(self):
        return get_test_context()

    def setUp(self):
        super(ScenarioTestCase, self).setUp()
        if self.patch_task_utils:
            self.mock_resource_is = fixtures.MockPatch(
                self.task_utils + ".resource_is")
            self.mock_get_from_manager = fixtures.MockPatch(
                self.task_utils + ".get_from_manager")
            self.mock_wait_for = fixtures.MockPatch(
                self.task_utils + ".wait_for")
            self.mock_wait_for_delete = fixtures.MockPatch(
                self.task_utils + ".wait_for_delete")
            self.mock_wait_for_status = fixtures.MockPatch(
                self.task_utils + ".wait_for_status")
            self.useFixture(self.mock_resource_is)
            self.useFixture(self.mock_get_from_manager)
            self.useFixture(self.mock_wait_for)
            self.useFixture(self.mock_wait_for_delete)
            self.useFixture(self.mock_wait_for_status)

        self.mock_sleep = fixtures.MockPatch("time.sleep")
        self.useFixture(self.mock_sleep)

        self._clients = {}
        self._client_mocks = self.get_client_mocks()

        for patcher in self._client_mocks:
            patcher.start()

        self.context = self.get_test_context()

    def tearDown(self):
        for patcher in self._client_mocks:
            patcher.stop()
        super(ScenarioTestCase, self).tearDown()


class ContextClientAdapter(object):
    def __init__(self, endpoint, test_case):
        self.endpoint = endpoint
        self.test_case = test_case

    def mock_client(self, name, version=None):
        admin = self.endpoint.startswith("admin")
        client = self.test_case.clients(name, version=version, admin=admin)
        if not isinstance(client.return_value, mock.Mock):
            return client.return_value
        if client.side_effect is not None:
            # NOTE(pboldin): if a client has side_effects that means the
            # user wants some of the returned values overrided (look at
            # the test_existing_users for instance)
            return client()
        return client

    def __getattr__(self, name):
        # NOTE(pboldin): __getattr__ magic is called last, after the value
        # were looked up for in __dict__
        return lambda version=None: self.mock_client(name, version)


class ContextTestCase(ScenarioTestCase):
    def setUp(self):
        super(ContextTestCase, self).setUp()

        self._adapters = {}

    def context_client(self, endpoint, api_info=None):
        if endpoint not in self._adapters:
            self._adapters[endpoint] = ContextClientAdapter(endpoint, self)
        return self._adapters[endpoint]

    def get_client_mocks(self):
        return [
            mock.patch(
                "rally.plugins.openstack.osclients.Clients",
                mock.Mock(side_effect=self.context_client))
        ]


class FakeClientsScenarioTestCase(ScenarioTestCase):
    """Base class for Scenario tests using fake (not mocked) self.clients."""

    def client_factory(self, client_type, version=None, admin=False):
        return getattr(self._fake_clients, client_type)()

    def setUp(self):
        super(FakeClientsScenarioTestCase, self).setUp()
        self._fake_clients = fakes.FakeClients()


def get_test_context(**kwargs):
    kwargs["task"] = {"uuid": str(uuid.uuid4())}
    kwargs["owner_id"] = str(uuid.uuid4())
    return kwargs
