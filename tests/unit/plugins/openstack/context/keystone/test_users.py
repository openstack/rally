# Copyright 2014: Mirantis Inc.
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

from rally import consts
from rally import exceptions
from rally.plugins.openstack.context.keystone import users
from rally.plugins.openstack import credential as oscredential
from tests.unit import test

CTX = "rally.plugins.openstack.context.keystone.users"


class UserGeneratorBaseTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(UserGeneratorBaseTestCase, self).setUp()
        self.osclients_patcher = mock.patch("%s.osclients" % CTX)
        self.osclients = self.osclients_patcher.start()
        self.addCleanup(self.osclients_patcher.stop)

        self.deployment_uuid = "deployment_id"

        self.admin_cred = {
            "username": "root", "password": "qwerty",
            "auth_url": "https://example.com",
            "project_domain_name": "foo",
            "user_domain_name": "bar"}

        self.platforms = {
            "openstack": {
                "admin": self.admin_cred,
                "users": []
            }
        }

        self.context.update({
            "config": {"users": {}},
            "env": {"platforms": self.platforms},
            "task": {"uuid": "task_id",
                     "deployment_uuid": self.deployment_uuid}
        })

    def test___init__for_new_users(self):
        self.context["config"]["users"] = {
            "tenants": 1, "users_per_tenant": 1,
            "resource_management_workers": 1}

        user_generator = users.UserGenerator(self.context)

        self.assertEqual([], user_generator.existing_users)
        self.assertEqual(self.admin_cred["project_domain_name"],
                         user_generator.config["project_domain"])
        self.assertEqual(self.admin_cred["user_domain_name"],
                         user_generator.config["user_domain"])

        # the case #2 - existing users are presented in deployment but
        #   the user forces to create new ones
        self.platforms["openstack"]["users"] = [mock.Mock()]

        user_generator = users.UserGenerator(self.context)

        self.assertEqual([], user_generator.existing_users)
        self.assertEqual(self.admin_cred["project_domain_name"],
                         user_generator.config["project_domain"])
        self.assertEqual(self.admin_cred["user_domain_name"],
                         user_generator.config["user_domain"])

    def test___init__for_existing_users(self):
        foo_user = mock.Mock()

        self.platforms["openstack"]["users"] = [foo_user]

        user_generator = users.UserGenerator(self.context)

        self.assertEqual([foo_user], user_generator.existing_users)
        self.assertEqual({"user_choice_method": "random"},
                         user_generator.config)

        # the case #2: the config with `user_choice_method` option
        self.context["config"]["users"] = {"user_choice_method": "foo"}

        user_generator = users.UserGenerator(self.context)

        self.assertEqual([foo_user], user_generator.existing_users)
        self.assertEqual({"user_choice_method": "foo"}, user_generator.config)

    def test_setup(self):
        user_generator = users.UserGenerator(self.context)
        user_generator.use_existing_users = mock.Mock()
        user_generator.create_users = mock.Mock()

        # no existing users -> new users should be created
        user_generator.existing_users = []

        user_generator.setup()

        user_generator.create_users.assert_called_once_with()
        self.assertFalse(user_generator.use_existing_users.called)

        user_generator.create_users.reset_mock()
        user_generator.use_existing_users.reset_mock()

        # existing_users is not empty -> existing users should be created
        user_generator.existing_users = [mock.Mock()]

        user_generator.setup()

        user_generator.use_existing_users.assert_called_once_with()
        self.assertFalse(user_generator.create_users.called)

    def test_cleanup(self):
        user_generator = users.UserGenerator(self.context)
        user_generator._remove_default_security_group = mock.Mock()
        user_generator._delete_users = mock.Mock()
        user_generator._delete_tenants = mock.Mock()

        # In case if existing users nothing should be done
        user_generator.existing_users = [mock.Mock]

        user_generator.cleanup()

        self.assertFalse(user_generator._remove_default_security_group.called)
        self.assertFalse(user_generator._delete_users.called)
        self.assertFalse(user_generator._delete_tenants.called)

        # In case when new users were created, the proper cleanup should be
        #   performed
        user_generator.existing_users = []

        user_generator.cleanup()

        user_generator._remove_default_security_group.assert_called_once_with()
        user_generator._delete_users.assert_called_once_with()
        user_generator._delete_tenants.assert_called_once_with()


class UserGeneratorForExistingUsersTestCase(test.ScenarioTestCase):
    def setUp(self):
        super(UserGeneratorForExistingUsersTestCase, self).setUp()
        self.osclients_patcher = mock.patch("%s.osclients" % CTX)
        self.osclients = self.osclients_patcher.start()
        self.addCleanup(self.osclients_patcher.stop)

        self.deployment_uuid = "deployment_id"

        self.platforms = {
            "openstack": {
                "admin": {"username": "root",
                          "password": "qwerty",
                          "auth_url": "https://example.com"},
                "users": []
            }
        }
        self.context.update({
            "config": {"users": {}},
            "users": [],
            "env": {"platforms": self.platforms},
            "task": {"uuid": "task_id",
                     "deployment_uuid": self.deployment_uuid}
        })

    @mock.patch("%s.credential.OpenStackCredential" % CTX)
    @mock.patch("%s.osclients.Clients" % CTX)
    def test_use_existing_users(self, mock_clients,
                                mock_open_stack_credential):
        user1 = {"tenant_name": "proj", "username": "usr",
                 "password": "pswd", "auth_url": "https://example.com"}
        user2 = {"tenant_name": "proj", "username": "usr",
                 "password": "pswd", "auth_url": "https://example.com"}
        user3 = {"tenant_name": "proj", "username": "usr",
                 "password": "pswd", "auth_url": "https://example.com"}

        user_list = [user1, user2, user3]

        class AuthRef(object):
            USER_ID_COUNT = 0
            PROJECT_ID_COUNT = 0

            @property
            def user_id(self):
                self.USER_ID_COUNT += 1
                return "u%s" % self.USER_ID_COUNT

            @property
            def project_id(self):
                self.PROJECT_ID_COUNT += 1
                return "p%s" % (self.PROJECT_ID_COUNT % 2)

        auth_ref = AuthRef()

        mock_clients.return_value.keystone.auth_ref = auth_ref

        self.platforms["openstack"]["users"] = user_list

        user_generator = users.UserGenerator(self.context)
        user_generator.setup()

        self.assertIn("users", self.context)
        self.assertIn("tenants", self.context)
        self.assertIn("user_choice_method", self.context)
        self.assertEqual("random", self.context["user_choice_method"])

        creds = mock_open_stack_credential.return_value
        self.assertEqual(
            [{"id": "u1", "credential": creds, "tenant_id": "p1"},
             {"id": "u2", "credential": creds, "tenant_id": "p0"},
             {"id": "u3", "credential": creds, "tenant_id": "p1"}],
            self.context["users"]
        )
        self.assertEqual({"p0": {"id": "p0", "name": creds.tenant_name},
                          "p1": {"id": "p1", "name": creds.tenant_name}},
                         self.context["tenants"])


class UserGeneratorForNewUsersTestCase(test.ScenarioTestCase):

    tenants_num = 1
    users_per_tenant = 5
    users_num = tenants_num * users_per_tenant
    threads = 10

    def setUp(self):
        super(UserGeneratorForNewUsersTestCase, self).setUp()
        self.osclients_patcher = mock.patch("%s.osclients" % CTX)
        self.osclients = self.osclients_patcher.start()
        self.addCleanup(self.osclients_patcher.stop)

        # Force the case of creating new users
        self.platforms = {
            "openstack": {
                "admin": {"username": "root",
                          "password": "qwerty",
                          "auth_url": "https://example.com"},
                "users": []
            }
        }

        self.context.update({
            "config": {
                "users": {
                    "tenants": self.tenants_num,
                    "users_per_tenant": self.users_per_tenant,
                    "resource_management_workers": self.threads,
                }
            },
            "env": {"platforms": self.platforms},
            "users": [],
            "task": {"uuid": "task_id", "deployment_uuid": "dep_uuid"}
        })

    @mock.patch("%s.network.wrap" % CTX)
    def test__remove_default_security_group_not_needed(self, mock_wrap):
        services = {"compute": consts.Service.NOVA}
        self.osclients.Clients().services.return_value = services
        user_generator = users.UserGenerator(self.context)
        user_generator._remove_default_security_group()
        self.assertFalse(mock_wrap.called)

    @mock.patch("%s.network.wrap" % CTX)
    def test__remove_default_security_group_neutron_no_sg(self, mock_wrap):
        net_wrapper = mock.Mock(SERVICE_IMPL=consts.Service.NEUTRON)
        net_wrapper.supports_extension.return_value = (False, None)
        mock_wrap.return_value = net_wrapper

        user_generator = users.UserGenerator(self.context)

        admin_clients = mock.Mock()
        admin_clients.services.return_value = {
            "compute": consts.Service.NOVA,
            "neutron": consts.Service.NEUTRON}
        user_clients = [mock.Mock(), mock.Mock()]
        self.osclients.Clients.side_effect = [admin_clients] + user_clients

        user_generator._remove_default_security_group()

        mock_wrap.assert_called_once_with(admin_clients, user_generator)
        net_wrapper.supports_extension.assert_called_once_with(
            "security-group")

    @mock.patch("rally.common.utils.iterate_per_tenants")
    @mock.patch("%s.network" % CTX)
    def test__remove_default_security_group(self, mock_network,
                                            mock_iterate_per_tenants):
        net_wrapper = mock.Mock(SERVICE_IMPL=consts.Service.NEUTRON)
        net_wrapper.supports_extension.return_value = (True, None)
        mock_network.wrap.return_value = net_wrapper

        user_generator = users.UserGenerator(self.context)

        admin_clients = mock.Mock()
        admin_clients.services.return_value = {
            "compute": consts.Service.NOVA,
            "neutron": consts.Service.NEUTRON}
        user1 = mock.Mock()
        user1.neutron.return_value.list_security_groups.return_value = {
            "security_groups": [{"id": "id-1", "name": "default"},
                                {"id": "id-2", "name": "not-default"}]}
        user2 = mock.Mock()
        user2.neutron.return_value.list_security_groups.return_value = {
            "security_groups": [{"id": "id-3", "name": "default"},
                                {"id": "id-4", "name": "not-default"}]}
        user_clients = [user1, user2]
        self.osclients.Clients.side_effect = [admin_clients] + user_clients

        mock_iterate_per_tenants.return_value = [
            (mock.MagicMock(), "t1"),
            (mock.MagicMock(), "t2")]

        user_generator._remove_default_security_group()

        mock_network.wrap.assert_called_once_with(admin_clients,
                                                  user_generator)

        mock_iterate_per_tenants.assert_called_once_with(
            user_generator.context["users"])
        expected = [mock.call(user_generator.credential)] + [
            mock.call(u["credential"])
            for u, t in mock_iterate_per_tenants.return_value]
        self.osclients.Clients.assert_has_calls(expected, any_order=True)

        user_net = user1.neutron.return_value
        user_net.list_security_groups.assert_called_once_with(tenant_id="t1")
        user_net = user2.neutron.return_value
        user_net.list_security_groups.assert_called_once_with(tenant_id="t2")
        admin_neutron = admin_clients.neutron.return_value
        self.assertEqual(
            [mock.call("id-1"), mock.call("id-3")],
            admin_neutron.delete_security_group.call_args_list)

    @mock.patch("%s.identity" % CTX)
    def test__create_tenants(self, mock_identity):
        self.context["config"]["users"]["tenants"] = 1
        user_generator = users.UserGenerator(self.context)
        tenants = user_generator._create_tenants()
        self.assertEqual(1, len(tenants))
        id, tenant = tenants.popitem()
        self.assertIn("name", tenant)

    @mock.patch("%s.identity" % CTX)
    def test__create_users(self, mock_identity):
        self.context["config"]["users"]["users_per_tenant"] = 2
        user_generator = users.UserGenerator(self.context)
        user_generator.context["tenants"] = {"t1": {"id": "t1", "name": "t1"},
                                             "t2": {"id": "t2", "name": "t2"}}
        users_ = user_generator._create_users()
        self.assertEqual(4, len(users_))
        for user in users_:
            self.assertIn("id", user)
            self.assertIn("credential", user)

    @mock.patch("%s.identity" % CTX)
    def test__delete_tenants(self, mock_identity):
        user_generator = users.UserGenerator(self.context)
        user_generator.context["tenants"] = {"t1": {"id": "t1", "name": "t1"},
                                             "t2": {"id": "t2", "name": "t2"}}
        user_generator._delete_tenants()
        self.assertEqual(0, len(user_generator.context["tenants"]))

    @mock.patch("%s.identity" % CTX)
    def test__delete_tenants_failure(self, mock_identity):
        identity_service = mock_identity.Identity.return_value
        identity_service.delete_project.side_effect = Exception()
        user_generator = users.UserGenerator(self.context)
        user_generator.context["tenants"] = {"t1": {"id": "t1", "name": "t1"},
                                             "t2": {"id": "t2", "name": "t2"}}
        user_generator._delete_tenants()
        self.assertEqual(0, len(user_generator.context["tenants"]))

    @mock.patch("%s.identity" % CTX)
    def test__delete_users(self, mock_identity):
        user_generator = users.UserGenerator(self.context)
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        user_generator.context["users"] = [user1, user2]
        user_generator._delete_users()
        self.assertEqual(0, len(user_generator.context["users"]))

    @mock.patch("%s.identity" % CTX)
    def test__delete_users_failure(self, mock_identity):
        identity_service = mock_identity.Identity.return_value
        identity_service.delete_user.side_effect = Exception()
        user_generator = users.UserGenerator(self.context)
        user1 = mock.MagicMock()
        user2 = mock.MagicMock()
        user_generator.context["users"] = [user1, user2]
        user_generator._delete_users()
        self.assertEqual(0, len(user_generator.context["users"]))

    @mock.patch("%s.identity" % CTX)
    def test_setup_and_cleanup(self, mock_identity):
        with users.UserGenerator(self.context) as ctx:

            ctx.setup()

            self.assertEqual(self.users_num,
                             len(ctx.context["users"]))
            self.assertEqual(self.tenants_num,
                             len(ctx.context["tenants"]))

            self.assertEqual("random", ctx.context["user_choice_method"])

        # Cleanup (called by content manager)
        self.assertEqual(0, len(ctx.context["users"]))
        self.assertEqual(0, len(ctx.context["tenants"]))

    @mock.patch("rally.common.broker.LOG.warning")
    @mock.patch("%s.identity" % CTX)
    def test_setup_and_cleanup_with_error_during_create_user(
            self, mock_identity, mock_log_warning):
        identity_service = mock_identity.Identity.return_value
        identity_service.create_user.side_effect = Exception()
        with users.UserGenerator(self.context) as ctx:
                self.assertRaises(exceptions.ContextSetupFailure, ctx.setup)
                mock_log_warning.assert_called_with(
                    "Failed to consume a task from the queue: ")

        # Ensure that tenants get deleted anyway
        self.assertEqual(0, len(ctx.context["tenants"]))

    @mock.patch("%s.identity" % CTX)
    def test_users_and_tenants_in_context(self, mock_identity):
        identity_service = mock_identity.Identity.return_value

        credential = oscredential.OpenStackCredential(
            "foo_url", "foo", "foo_pass",
            https_insecure=True,
            https_cacert="cacert")
        tmp_context = dict(self.context)
        tmp_context["config"]["users"] = {"tenants": 1,
                                          "users_per_tenant": 2,
                                          "resource_management_workers": 1}
        tmp_context["env"]["platforms"]["openstack"]["admin"] = credential

        credential_dict = credential.to_dict()
        user_list = [mock.MagicMock(id="id_%d" % i)
                     for i in range(self.users_num)]
        identity_service.create_user.side_effect = user_list

        with users.UserGenerator(tmp_context) as ctx:
            ctx.generate_random_name = mock.Mock()
            ctx.setup()

            create_tenant_calls = []
            for i, t in enumerate(ctx.context["tenants"]):
                create_tenant_calls.append(
                    mock.call(ctx.generate_random_name.return_value,
                              ctx.config["project_domain"]))

            for user in ctx.context["users"]:
                self.assertEqual(set(["id", "credential", "tenant_id"]),
                                 set(user.keys()))

                user_credential_dict = user["credential"].to_dict()

                excluded_keys = ["auth_url", "username", "password",
                                 "tenant_name", "region_name",
                                 "project_domain_name",
                                 "user_domain_name", "permission"]
                for key in (set(credential_dict.keys()) - set(excluded_keys)):
                    self.assertEqual(credential_dict[key],
                                     user_credential_dict[key],
                                     "The key '%s' differs." % key)

            tenants_ids = []
            for t in ctx.context["tenants"].keys():
                tenants_ids.append(t)

            for (user, tenant_id, orig_user) in zip(ctx.context["users"],
                                                    tenants_ids, user_list):
                self.assertEqual(orig_user.id, user["id"])
                self.assertEqual(tenant_id, user["tenant_id"])

    @mock.patch("%s.identity" % CTX)
    def test_users_contains_correct_endpoint_type(self, mock_identity):
        credential = oscredential.OpenStackCredential(
            "foo_url", "foo", "foo_pass",
            endpoint_type=consts.EndpointType.INTERNAL)
        config = {
            "config": {
                "users": {
                    "tenants": 1,
                    "users_per_tenant": 2,
                    "resource_management_workers": 1
                }
            },
            "env": {"platforms": {"openstack": {"admin": credential,
                                                "users": []}}},
            "task": {"uuid": "task_id", "deployment_uuid": "deployment_id"}
        }

        user_generator = users.UserGenerator(config)
        users_ = user_generator._create_users()

        for user in users_:
            self.assertEqual("internal", user["credential"].endpoint_type)

    @mock.patch("%s.identity" % CTX)
    def test_users_contains_default_endpoint_type(self, mock_identity):
        credential = oscredential.OpenStackCredential(
            "foo_url", "foo", "foo_pass")
        config = {
            "config": {
                "users": {
                    "tenants": 1,
                    "users_per_tenant": 2,
                    "resource_management_workers": 1
                }
            },
            "env": {"platforms": {"openstack": {"admin": credential,
                                                "users": []}}},
            "task": {"uuid": "task_id", "deployment_uuid": "deployment_id"}
        }

        user_generator = users.UserGenerator(config)
        users_ = user_generator._create_users()

        for user in users_:
            self.assertEqual("public", user["credential"].endpoint_type)
