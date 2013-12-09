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

"""Tests for utils."""
import mock
import multiprocessing
import os
import tempfile
import time

from rally.benchmark import base
from rally.benchmark import config
from rally.benchmark import utils
from rally import test
from rally import utils as rally_utils
from tests.benchmark.scenarios.nova import test_utils


class FakeScenario(base.Scenario):

    @classmethod
    def class_init(cls, endpoints):
        pass

    @classmethod
    def do_it(cls, **kwargs):
        pass

    @classmethod
    def too_long(cls, **kwargs):
        pass

    @classmethod
    def something_went_wrong(cls, **kwargs):
        raise Exception("Something went wrong")


class FakeTimer(rally_utils.Timer):

    def duration(self):
        return 10


class MockedPool(object):

    def __init__(self, concurrent=1):
        pass

    def close(self):
        pass

    def join(self):
        pass

    def apply_async(self, func, args=()):
        func(*args)


class ScenarioTestCase(test.TestCase):

    def setUp(self):
        super(ScenarioTestCase, self).setUp()
        admin_keys = ["admin_username", "admin_password",
                      "admin_tenant_name", "uri"]
        self.fake_kw = dict(zip(admin_keys, admin_keys))

    def test_init_calls_register(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            with mock.patch("rally.benchmark.utils.base") as mock_base:
                utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            self.assertEqual(mock_base.mock_calls,
                             [mock.call.Scenario.register()])

    def test_create_temp_tenants_and_users(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            tenants = 10
            users_per_tenant = 5
            endpoints = runner._create_temp_tenants_and_users(tenants,
                                                              users_per_tenant)
            self.assertEqual(len(endpoints), tenants * users_per_tenant)
            endpoint_keys = set(["username", "password", "tenant_name", "uri"])
            for endpoint in endpoints:
                self.assertEqual(set(endpoint.keys()), endpoint_keys)

    def test_run_scenario(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            with mock.patch("rally.benchmark.utils.utils") as mock_utils:
                runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
                utils.__openstack_clients__ = ["client"]
                active_users = 2
                times = 3
                duration = 0.01

                mock_utils.Timer = FakeTimer
                results = runner._run_scenario(FakeScenario, "do_it", {},
                                               "continuous",
                                               {"times": times,
                                                "active_users": active_users,
                                                "timeout": 2})
                expected = [{"time": 10, "idle_time": 0, "error": None}
                            for i in range(times)]
                self.assertEqual(results, expected)

                results = runner._run_scenario(FakeScenario, "do_it", {},
                                               "continuous",
                                               {"duration": duration,
                                                "active_users": active_users,
                                                "timeout": 2})
                expected = [{"time": 10, "idle_time": 0, "error": None}
                            for i in range(active_users)]
                self.assertEqual(results, expected)

    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("multiprocessing.pool.IMapIterator.next")
    @mock.patch("rally.benchmark.utils.time.time")
    def test_run_scenario_timeout(self, mock_time, mock_next, mock_osclients):
        mock_time.side_effect = [1, 2, 3, 10]
        mock_next.side_effect = multiprocessing.TimeoutError()
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        utils.__openstack_clients__ = ["client"]
        times = 4
        active_users = 2
        results = runner._run_scenario(FakeScenario, "too_long", {},
                                       "continuous",
                                       {"times": times,
                                        "active_users": active_users,
                                        "timeout": 0.01})
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

        duration = 0.1
        results = runner._run_scenario(FakeScenario, "too_long", {},
                                       "continuous",
                                       {"duration": duration,
                                        "active_users": active_users,
                                        "timeout": 0.01})
        self.assertEqual(len(results), active_users)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

    def test_run_scenario_exception_inside_test(self):
        with mock.patch("rally.benchmark.utils.osclients") as mock_osclients:
            mock_osclients.Clients.return_value = test_utils.FakeClients()
            runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
            utils.__openstack_clients__ = ["client"]
            times = 1
            duration = 0.01
            active_users = 2
            with mock.patch("rally.benchmark.utils.utils") as mock_utils:
                mock_utils.Timer = FakeTimer
                results = runner._run_scenario(FakeScenario,
                                               "something_went_wrong", {},
                                               "continuous",
                                               {"times": times,
                                                "active_users": active_users,
                                                "timeout": 1})
                self.assertEqual(len(results), times)
                for r in results:
                    self.assertEqual(r['time'], 10)
                    self.assertEqual(r['error'][:2],
                                     [str(Exception), "Something went wrong"])

                results = runner._run_scenario(FakeScenario,
                                               "something_went_wrong", {},
                                               "continuous",
                                               {"duration": duration,
                                                "active_users": active_users,
                                                "timeout": 1})
                self.assertEqual(len(results), active_users)
                for r in results:
                    self.assertEqual(r['time'], 10)
                    self.assertEqual(r['error'][:2],
                                     [str(Exception), "Something went wrong"])

    def test_run_scenario_exception_outside_test(self):
        pass

    @mock.patch("rally.benchmark.utils.multiprocessing")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously_for_times(self, mock_osclients,
                                                 mock_multi):
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        utils.__openstack_clients__ = ["client"]
        times = 3
        active_users = 4
        timeout = 5
        mock_multi.Pool = mock.MagicMock()
        runner._run_scenario_continuously_for_times(FakeScenario, "do_it", {},
                                                    times, active_users,
                                                    timeout)
        expect = [
            mock.call(active_users),
            mock.call().imap(
                utils._run_scenario_loop,
                [(i, FakeScenario, "do_it", {})
                    for i in xrange(times)]
            )
        ]
        expect.extend([mock.call().imap().next(timeout) for i in range(times)])
        expect.extend([
            mock.call().close(),
            mock.call().join()
        ])
        self.assertEqual(mock_multi.Pool.mock_calls, expect)

    @mock.patch("rally.benchmark.utils._infinite_run_args")
    @mock.patch("rally.benchmark.utils.multiprocessing")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously_for_duration(self, mock_osclients,
                                                    mock_multi, mock_generate):
        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        utils.__openstack_clients__ = ["client"]
        duration = 0
        active_users = 4
        timeout = 5
        mock_multi.Pool = mock.MagicMock()
        mock_generate.return_value = {}
        runner._run_scenario_continuously_for_duration(FakeScenario,
                                                       "do_it", {}, duration,
                                                       active_users, timeout)
        expect = [
            mock.call(active_users),
            mock.call().imap(utils._run_scenario_loop, {}),
            mock.call().terminate(),
            mock.call().join()
        ]
        self.assertEqual(mock_multi.Pool.mock_calls, expect)

    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.utils.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_continuously(self, mock_osclients, mock_base,
                                       mock_clients):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        runner._run_scenario_continuously_for_times = \
            mock.MagicMock(return_value="result")
        runner._run_scenario_continuously_for_duration = \
            mock.MagicMock(return_value="result")
        runner._create_temp_tenants_and_users = mock.MagicMock(
                                                            return_value=[])
        runner._delete_temp_tenants_and_users = mock.MagicMock()

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        mock_clients.return_value = ["client"]
        result = runner._run_scenario(FakeScenario, "do_it", {"a": 1},
                                      "continuous", {"times": 2,
                                                     "active_users": 3,
                                                     "timeout": 1})
        self.assertEqual(result, "result")
        runner._run_scenario_continuously_for_times.assert_called_once_with(
                                    FakeScenario, "do_it", {"a": 1}, 2, 3, 1)
        result = runner._run_scenario(FakeScenario, "do_it", {"a": 1},
                                      "continuous", {"duration": 2,
                                                     "active_users": 3,
                                                     "timeout": 1})
        self.assertEqual(result, "result")
        runner._run_scenario_continuously_for_duration.assert_called_once_with(
                                    FakeScenario, "do_it", {"a": 1}, 2, 3, 1)

    @mock.patch("rally.benchmark.utils._create_openstack_clients")
    @mock.patch("rally.benchmark.utils.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run(self, mock_osclients, mock_base, mock_clients):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_osclients.Clients.return_value = test_utils.FakeClients()
        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        runner._run_scenario = mock.MagicMock(return_value="result")
        runner._create_temp_tenants_and_users = mock.MagicMock(
                                                        return_value=[])
        runner._delete_temp_tenants_and_users = mock.MagicMock()

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        result = runner.run("FakeScenario.do_it", {})
        self.assertEqual(result, "result")
        runner.run("FakeScenario.do_it",
                   {"args": {"a": 1}, "init": {"arg": 1},
                    "config": {"timeout": 1, "times": 2, "active_users": 3,
                               "tenants": 5, "users_per_tenant": 2}})
        runner.run("FakeScenario.do_it",
                   {"args": {"a": 1}, "init": {"fake": "arg"},
                    "execution_type": "continuous",
                    "config": {"timeout": 1, "duration": 40, "active_users": 3,
                               "tenants": 5, "users_per_tenant": 2}})

        expected = [
            mock.call(FakeScenario, "do_it", {}, "continuous", {}),
            mock.call(FakeScenario, "do_it", {"a": 1}, "continuous",
                      {"timeout": 1, "times": 2, "active_users": 3,
                       "tenants": 5, "users_per_tenant": 2}),
            mock.call(FakeScenario, "do_it", {"a": 1}, "continuous",
                      {"timeout": 1, "duration": 40, "active_users": 3,
                       "tenants": 5, "users_per_tenant": 2})
        ]
        self.assertEqual(runner._run_scenario.mock_calls, expected)

        expected = [
            mock.call(1, 1),
            mock.call(5, 2),
            mock.call(5, 2)
        ]
        self.assertEqual(runner._create_temp_tenants_and_users.mock_calls,
                         expected)

        expected = [
            mock.call.init({}),
            mock.call.init({"arg": 1}),
            mock.call.init({"fake": "arg"}),
        ]
        self.assertEqual(FakeScenario.mock_calls, expected)

    @mock.patch("rally.benchmark.utils._create_openstack_clients")
    @mock.patch("rally.benchmark.utils.base")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("multiprocessing.Pool")
    def test_generic_cleanup(self, mock_pool, mock_osclients,
                             mock_base, mock_clients):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})

        mock_cms = [test_utils.FakeClients(), test_utils.FakeClients(),
                    test_utils.FakeClients()]
        clients = [
            dict((
                ("nova", cl.get_nova_client()),
                ("keystone", cl.get_keystone_client()),
                ("glance", cl.get_glance_client()),
                ("cinder", cl.get_cinder_client())
            )) for cl in mock_cms
        ]
        mock_clients.return_value = clients

        runner = utils.ScenarioRunner(mock.MagicMock(), self.fake_kw)
        runner._run_scenario = mock.MagicMock(return_value="result")
        runner._create_temp_tenants_and_users = mock.MagicMock(
                                                        return_value=[])
        runner._delete_temp_tenants_and_users = mock.MagicMock()

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)

        for index in range(len(clients)):
            client = clients[index]
            nova = client["nova"]
            cinder = client["cinder"]
            for count in range(3):
                uid = index + count
                img = nova.images.create()
                nova.servers.create("svr-%s" % (uid), img.uuid, index)
                nova.keypairs.create("keypair-%s" % (uid))
                nova.security_groups.create("secgroup-%s" % (uid))
                nova.networks.create("net-%s" % (uid))
                cinder.volumes.create("vol-%s" % (uid))
                cinder.volume_types.create("voltype-%s" % (uid))
                cinder.transfers.create("voltransfer-%s" % (uid))
                cinder.volume_snapshots.create("snap-%s" % (uid))
                cinder.backups.create("backup-%s" % (uid))

        mock_pool.return_value = MockedPool()

        runner.run("FakeScenario.do_it",
                   {"args": {"a": 1}, "init": {"arg": 1},
                    "config": {"timeout": 1, "times": 2, "active_users": 3,
                               "tenants": 5, "users_per_tenant": 2}})

        def _assert_purged(manager, resource_type):
            resources = manager.list()
            self.assertEqual([], resources, "%s not purged: %s" %
                             (resource_type, resources))

        for client in clients:
            nova = client["nova"]
            cinder = client["cinder"]
            _assert_purged(nova.servers, "servers")
            _assert_purged(nova.keypairs, "key pairs")
            _assert_purged(nova.security_groups, "security groups")
            _assert_purged(nova.networks, "networks")

            _assert_purged(cinder.volumes, "volumes")
            _assert_purged(cinder.volume_types, "volume types")
            _assert_purged(cinder.backups, "volume backups")
            _assert_purged(cinder.transfers, "volume transfers")
            _assert_purged(cinder.volume_snapshots, "volume snapshots")

            for image in nova.images.list():
                self.assertEqual("DELETED", image.status,
                                 "image not purged: %s" % (image))


def test_dummy_1():
    pass


def test_dummy_2():
    pass


def test_dummy_timeout():
    time.sleep(1.1)


class VerifierTestCase(test.TestCase):

    def setUp(self):
        super(VerifierTestCase, self).setUp()
        self.cloud_config_manager = config.CloudConfigManager()
        self.cloud_config_fd, self.cloud_config_path = tempfile.mkstemp(
                                                suffix='rallycfg', text=True)
        with os.fdopen(self.cloud_config_fd, 'w') as f:
            self.cloud_config_manager.write(f)

    def tearDown(self):
        if os.path.exists(self.cloud_config_path):
            os.remove(self.cloud_config_path)
        super(VerifierTestCase, self).tearDown()

    def test_running_test(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            test = ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1']
            result = verifier.run(test)
            self.assertEqual(result['status'], 0)

    def test_running_multiple_tests(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        tests_dict = {
            'test1': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_1'],
            'test2': ['./tests/benchmark/test_utils.py', '-k', 'test_dummy_2']
        }
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            for result in verifier.run_all(tests_dict):
                self.assertEqual(result['status'], 0)

    def test_verifier_timeout(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '1']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            result = verifier.run(test)
            self.assertTrue('Timeout' in result['msg'])
            self.assertTrue(result['status'] != 0)

    def test_verifier_no_timeout(self):
        verifier = utils.Verifier(mock.MagicMock(), self.cloud_config_path)
        test = ['./tests/benchmark/test_utils.py', '-k',
                'test_dummy_timeout', '--timeout', '2']
        with mock.patch('rally.benchmark.utils.fuel_cleanup.cleanup'):
            result = verifier.run(test)
            self.assertTrue('Timeout' not in result['msg'])
            self.assertTrue(result['status'] == 0)
