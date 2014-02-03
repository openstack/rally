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

import mock
import multiprocessing

from rally.benchmark import runner
from rally.benchmark import validation
from rally import exceptions
from tests import fakes
from tests import test


class ScenarioRunnerTestCase(test.TestCase):

    def setUp(self):
        super(ScenarioRunnerTestCase, self).setUp()
        admin_keys = ["username", "password", "tenant_name", "auth_url"]
        self.fake_kw = dict(zip(admin_keys, admin_keys))

    @mock.patch("rally.benchmark.runner.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_init_calls_register(self, mock_osclients, mock_base):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        runner.ScenarioRunner.get_runner(mock.MagicMock(), self.fake_kw,
                                         {"execution": "continuous"})
        self.assertEqual(mock_base.mock_calls, [mock.call.Scenario.register()])

    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario(self, mock_osclients):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = runner.ScenarioRunner.get_runner(mock.MagicMock(),
                                                   self.fake_kw,
                                                   {"execution": "continuous"})
        runner.__openstack_clients__ = ["client"]
        active_users = 2
        times = 3
        duration = 0.01

        with mock.patch("rally.benchmark.runner.rutils") as mock_utils:
            mock_utils.Timer = fakes.FakeTimer
            results = srunner._run_scenario(fakes.FakeScenario, "do_it", {},
                                            {"times": times,
                                             "active_users": active_users,
                                             "timeout": 2})
            expected = [{"time": 10, "idle_time": 0, "error": None,
                         "scenario_output": None, "atomic_actions_time": []}
                        for i in range(times)]
            self.assertEqual(results, expected)

            results = srunner._run_scenario(fakes.FakeScenario, "do_it", {},
                                            {"duration": duration,
                                             "active_users": active_users,
                                             "timeout": 2})
            expected = [{"time": 10, "idle_time": 0, "error": None,
                         "scenario_output": None, "atomic_actions_time": []}
                        for i in range(active_users)]
            self.assertEqual(results, expected)

    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("multiprocessing.pool.IMapIterator.next")
    @mock.patch("rally.benchmark.runners.continuous.time.time")
    @mock.patch("rally.benchmark.utils._prepare_for_instance_ssh")
    def test_run_scenario_timeout(self, mock_prepare_for_instance_ssh,
                                  mock_time, mock_next, mock_osclients):

        mock_time.side_effect = [1, 2, 3, 10]
        mock_next.side_effect = multiprocessing.TimeoutError()
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = runner.ScenarioRunner.get_runner(mock.MagicMock(),
                                                   self.fake_kw,
                                                   {"execution": "continuous"})
        runner.__openstack_clients__ = ["client"]
        times = 4
        active_users = 2
        results = srunner._run_scenario(fakes.FakeScenario,
                                        "too_long", {},
                                        {"times": times,
                                         "active_users": active_users,
                                         "timeout": 0.01})
        self.assertEqual(len(results), times)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

        duration = 0.1
        results = srunner._run_scenario(fakes.FakeScenario,
                                        "too_long", {},
                                        {"duration": duration,
                                         "active_users": active_users,
                                         "timeout": 0.01})
        self.assertEqual(len(results), active_users)
        for r in results:
            self.assertEqual(r['time'], 0.01)
            self.assertEqual(r['error'][0],
                             str(multiprocessing.TimeoutError))

    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_scenario_exception_inside_test(self, mock_osclients):
        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = runner.ScenarioRunner.get_runner(
                mock.MagicMock(), self.fake_kw, {"execution": "continuous"})
        runner.__openstack_clients__ = ["client"]
        times = 1
        duration = 0.001
        active_users = 2

        # NOTE(msdubov): Should mock rutils here because we need them in
        #                ScenarioRunner.get_runner()
        with mock.patch("rally.benchmark.runner.rutils") as mock_utils:
            mock_utils.Timer = fakes.FakeTimer
            results = srunner._run_scenario(fakes.FakeScenario,
                                            "something_went_wrong", {},
                                            {"times": times, "timeout": 1,
                                             "active_users": active_users})
            self.assertEqual(len(results), times)
            for r in results:
                self.assertEqual(r['time'], 10)
                self.assertEqual(r['error'][:2],
                                 [str(Exception), "Something went wrong"])

            results = srunner._run_scenario(fakes.FakeScenario,
                                            "something_went_wrong", {},
                                            {"duration": duration,
                                             "timeout": 1,
                                             "active_users": active_users})
            self.assertEqual(len(results), active_users)
            for r in results:
                self.assertEqual(r['time'], 10)
                self.assertEqual(r['error'][:2],
                                 [str(Exception), "Something went wrong"])

    def test_run_scenario_exception_outside_test(self):
        pass

    def _set_mocks_for_run(self, mock_osclients, mock_base, validators=None):
        FakeScenario = mock.MagicMock()
        FakeScenario.init = mock.MagicMock(return_value={})
        if validators:
            FakeScenario.do_it.validators = validators

        mock_osclients.Clients.return_value = fakes.FakeClients()
        srunner = runner.ScenarioRunner.get_runner(mock.MagicMock(),
                                                   self.fake_kw,
                                                   {"execution": "continuous"})
        srunner._run_scenario = mock.MagicMock(return_value="result")

        mock_base.Scenario.get_by_name = \
            mock.MagicMock(return_value=FakeScenario)
        return FakeScenario, srunner

    @mock.patch("rally.benchmark.runner.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run(self, mock_osclients, mock_base):
        FakeScenario, srunner = self._set_mocks_for_run(mock_osclients,
                                                        mock_base)

        result = srunner.run("FakeScenario.do_it", {})
        self.assertEqual(result, "result")
        srunner.run("FakeScenario.do_it",
                    {"args": {"a": 1}, "init": {"arg": 1},
                     "config": {"timeout": 1, "times": 2, "active_users": 3,
                                "tenants": 5, "users_per_tenant": 2}})
        srunner.run("FakeScenario.do_it",
                    {"args": {"a": 1}, "init": {"fake": "arg"},
                     "execution_type": "continuous",
                     "config": {"timeout": 1, "duration": 40,
                                "active_users": 3, "tenants": 5,
                                "users_per_tenant": 2}})

        expected = [
            mock.call(FakeScenario, "do_it", {}, {}),
            mock.call(FakeScenario, "do_it", {"a": 1},
                      {"timeout": 1, "times": 2, "active_users": 3,
                       "tenants": 5, "users_per_tenant": 2}),
            mock.call(FakeScenario, "do_it", {"a": 1},
                      {"timeout": 1, "duration": 40, "active_users": 3,
                       "tenants": 5, "users_per_tenant": 2})
        ]
        self.assertEqual(srunner._run_scenario.mock_calls, expected)

    @mock.patch("rally.benchmark.runner.base")
    @mock.patch("rally.benchmark.utils.osclients")
    def test_run_validation_failure(self, mock_osclients, mock_base):
        def evil_validator(**kwargs):
            return validation.ValidationResult(is_valid=False)

        FakeScenario, srunner = self._set_mocks_for_run(mock_osclients,
                                                        mock_base,
                                                        [evil_validator])
        self.assertRaises(exceptions.InvalidScenarioArgument,
                          srunner.run, "FakeScenario.do_it", {})


class UserGeneratorTestCase(test.TestCase):

    def test_create_and_delete_users_and_tenants(self):
        admin_clients = {"keystone": fakes.FakeClients().get_keystone_client()}
        created_users = []
        created_tenants = []
        with runner.UserGenerator(admin_clients) as generator:
            tenants = 10
            users_per_tenant = 5
            endpoints = generator.create_users_and_tenants(tenants,
                                                           users_per_tenant)
            self.assertEqual(len(endpoints), tenants * users_per_tenant)
            endpoint_keys = set(["username", "password", "tenant_name",
                                 "auth_url"])
            for endpoint in endpoints:
                self.assertTrue(endpoint_keys.issubset(endpoint.keys()))
            created_users = generator.users
            created_tenants = generator.tenants
        self.assertTrue(all(u.status == "DELETED" for u in created_users))
        self.assertTrue(all(t.status == "DELETED" for t in created_tenants))


class ResourceCleanerTestCase(test.TestCase):

    @mock.patch("rally.benchmark.runner.base")
    @mock.patch("rally.benchmark.utils.osclients")
    @mock.patch("rally.benchmark.utils._delete_single_keystone_resource_type")
    def test_cleanup_resources(self, mock_del_single_keystone_res,
                               mock_osclients, mock_base):

        mock_cms = [fakes.FakeClients(), fakes.FakeClients(),
                    fakes.FakeClients()]
        clients = [
            dict((
                ("nova", cl.get_nova_client()),
                ("keystone", cl.get_keystone_client()),
                ("glance", cl.get_glance_client()),
                ("cinder", cl.get_cinder_client()),
                ("endpoint", cl.get_endpoint())
            )) for cl in mock_cms
        ]

        for index in range(len(clients)):
            client = clients[index]
            nova = client["nova"]
            cinder = client["cinder"]
            glance = client["glance"]
            for count in range(3):
                uid = index + count
                img = glance.images._create()
                nova.servers.create("svr-%s" % (uid), img.uuid, index)
                nova.keypairs.create("keypair-%s" % (uid))
                nova.security_groups.create("secgroup-%s" % (uid))
                nova.networks.create("net-%s" % (uid))
                cinder.volumes.create("vol-%s" % (uid))
                cinder.volume_types.create("voltype-%s" % (uid))
                cinder.transfers.create("voltransfer-%s" % (uid))
                cinder.volume_snapshots.create("snap-%s" % (uid))
                cinder.backups.create("backup-%s" % (uid))

        with runner.ResourceCleaner(admin=clients[0], users=clients):
            pass

        def _assert_purged(manager, resource_type):
            resources = manager.list()
            self.assertEqual([], resources, "%s not purged: %s" %
                             (resource_type, resources))

        for client in clients:
            nova = client["nova"]
            cinder = client["cinder"]
            glance = client["glance"]
            _assert_purged(nova.servers, "servers")
            _assert_purged(nova.keypairs, "key pairs")
            _assert_purged(nova.security_groups, "security groups")
            _assert_purged(nova.networks, "networks")

            _assert_purged(cinder.volumes, "volumes")
            _assert_purged(cinder.volume_types, "volume types")
            _assert_purged(cinder.backups, "volume backups")
            _assert_purged(cinder.transfers, "volume transfers")
            _assert_purged(cinder.volume_snapshots, "volume snapshots")

            for image in glance.images.list():
                self.assertEqual("DELETED", image.status,
                                 "image not purged: %s" % (image))

        expected = [mock.call(clients[0]["keystone"], resource) for
                    resource in ["users", "tenants", "services", "roles"]]

        self.assertEqual(mock_del_single_keystone_res.call_args_list, expected)
