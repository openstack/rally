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

from rally.common import utils
from rally.plugins.openstack.cleanup import base
from rally.plugins.openstack.cleanup import manager
from tests.unit import test


BASE = "rally.plugins.openstack.cleanup.manager"


class SeekAndDestroyTestCase(test.TestCase):

    def setUp(self):
        super(SeekAndDestroyTestCase, self).setUp()
        # clear out the client cache
        manager.SeekAndDestroy.cache = {}

    def test__get_cached_client(self):
        api_versions = {"cinder": {"version": "1", "service_type": "volume"}}

        destroyer = manager.SeekAndDestroy(None, None, None,
                                           api_versions=api_versions)
        cred = mock.Mock()
        user = {"credential": cred}

        clients = destroyer._get_cached_client(user)
        self.assertIs(cred.clients.return_value, clients)
        cred.clients.assert_called_once_with(api_info=api_versions)

        self.assertIsNone(destroyer._get_cached_client(None))

    @mock.patch("%s.LOG" % BASE)
    def test__delete_single_resource(self, mock_log):
        mock_resource = mock.MagicMock(_max_attempts=3, _timeout=10,
                                       _interval=0.01)
        mock_resource.delete.side_effect = [Exception, Exception, True]
        mock_resource.is_deleted.side_effect = [False, False, True]

        manager.SeekAndDestroy(None, None, None)._delete_single_resource(
            mock_resource)

        mock_resource.delete.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_resource.delete.call_count)
        mock_resource.is_deleted.assert_has_calls([mock.call()] * 3)
        self.assertEqual(3, mock_resource.is_deleted.call_count)

        # NOTE(boris-42): No logs and no exceptions means no bugs!
        self.assertEqual(0, mock_log.call_count)

    @mock.patch("%s.LOG" % BASE)
    def test__delete_single_resource_timeout(self, mock_log):

        mock_resource = mock.MagicMock(_max_attempts=1, _timeout=0.02,
                                       _interval=0.025)

        mock_resource.delete.return_value = True
        mock_resource.is_deleted.side_effect = [False, False, True]

        manager.SeekAndDestroy(None, None, None)._delete_single_resource(
            mock_resource)

        mock_resource.delete.assert_called_once_with()
        mock_resource.is_deleted.assert_called_once_with()

        self.assertEqual(1, mock_log.warning.call_count)

    @mock.patch("%s.LOG" % BASE)
    def test__delete_single_resource_excpetion_in_is_deleted(self, mock_log):
        mock_resource = mock.MagicMock(_max_attempts=3, _timeout=10,
                                       _interval=0)
        mock_resource.delete.return_value = True
        mock_resource.is_deleted.side_effect = [Exception] * 4
        manager.SeekAndDestroy(None, None, None)._delete_single_resource(
            mock_resource)

        mock_resource.delete.assert_called_once_with()
        self.assertEqual(4, mock_resource.is_deleted.call_count)

        self.assertEqual(1, mock_log.warning.call_count)
        self.assertEqual(4, mock_log.exception.call_count)

    def _manager(self, list_side_effect, **kw):
        mock_mgr = mock.MagicMock()
        mock_mgr().list.side_effect = list_side_effect
        mock_mgr.reset_mock()

        for k, v in kw.items():
            setattr(mock_mgr, k, v)

        return mock_mgr

    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    def test__publisher_admin(self, mock__get_cached_client):
        mock_mgr = self._manager([Exception, Exception, [1, 2, 3]],
                                 _perform_for_admin_only=False)
        admin = mock.MagicMock()
        publish = manager.SeekAndDestroy(mock_mgr, admin, None)._publisher

        queue = []
        publish(queue)
        mock__get_cached_client.assert_called_once_with(admin)
        mock_mgr.assert_called_once_with(
            admin=mock__get_cached_client.return_value)
        self.assertEqual(queue, [(admin, None, x) for x in range(1, 4)])

    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    def test__publisher_admin_only(self, mock__get_cached_client):
        mock_mgr = self._manager([Exception, Exception, [1, 2, 3]],
                                 _perform_for_admin_only=True)
        admin = mock.MagicMock()
        publish = manager.SeekAndDestroy(
            mock_mgr, admin, ["u1", "u2"])._publisher

        queue = []
        publish(queue)
        mock__get_cached_client.assert_called_once_with(admin)
        mock_mgr.assert_called_once_with(
            admin=mock__get_cached_client.return_value)
        self.assertEqual(queue, [(admin, None, x) for x in range(1, 4)])

    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    def test__publisher_user_resource(self, mock__get_cached_client):
        mock_mgr = self._manager([Exception, Exception, [1, 2, 3],
                                  Exception, Exception, [4, 5]],
                                 _perform_for_admin_only=False,
                                 _tenant_resource=True)

        admin = mock.MagicMock()
        users = [{"tenant_id": 1, "id": 1}, {"tenant_id": 2, "id": 2}]
        publish = manager.SeekAndDestroy(mock_mgr, admin, users)._publisher

        queue = []
        publish(queue)

        mock_client = mock__get_cached_client.return_value
        mock_mgr.assert_has_calls([
            mock.call(admin=mock_client, user=mock_client,
                      tenant_uuid=users[0]["tenant_id"]),
            mock.call().list(),
            mock.call().list(),
            mock.call().list(),
            mock.call(admin=mock_client, user=mock_client,
                      tenant_uuid=users[1]["tenant_id"]),
            mock.call().list(),
            mock.call().list()
        ])
        mock__get_cached_client.assert_has_calls([
            mock.call(admin),
            mock.call(users[0]),
            mock.call(users[1])
        ])
        expected_queue = [(admin, users[0], x) for x in range(1, 4)]
        expected_queue += [(admin, users[1], x) for x in range(4, 6)]
        self.assertEqual(expected_queue, queue)

    @mock.patch("%s.LOG" % BASE)
    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    def test__gen_publisher_tenant_resource(self, mock__get_cached_client,
                                            mock_log):
        mock_mgr = self._manager([Exception, [1, 2, 3],
                                  Exception, Exception, Exception,
                                  ["this shouldn't be in results"]],
                                 _perform_for_admin_only=False,
                                 _tenant_resource=True)
        users = [{"tenant_id": 1, "id": 1},
                 {"tenant_id": 1, "id": 2},
                 {"tenant_id": 2, "id": 3}]

        publish = manager.SeekAndDestroy(
            mock_mgr, None, users)._publisher

        queue = []
        publish(queue)

        mock_client = mock__get_cached_client.return_value
        mock_mgr.assert_has_calls([
            mock.call(admin=mock_client, user=mock_client,
                      tenant_uuid=users[0]["tenant_id"]),
            mock.call().list(),
            mock.call().list(),
            mock.call(admin=mock_client, user=mock_client,
                      tenant_uuid=users[2]["tenant_id"]),
            mock.call().list(),
            mock.call().list(),
            mock.call().list()
        ])
        mock__get_cached_client.assert_has_calls([
            mock.call(None),
            mock.call(users[0]),
            mock.call(users[2])
        ])
        self.assertEqual(queue, [(None, users[0], x) for x in range(1, 4)])
        self.assertTrue(mock_log.warning.mock_called)
        self.assertTrue(mock_log.exception.mock_called)

    @mock.patch("rally.common.utils.name_matches_object")
    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    @mock.patch("%s.SeekAndDestroy._delete_single_resource" % BASE)
    def test__consumer(self, mock__delete_single_resource,
                       mock__get_cached_client,
                       mock_name_matches_object):
        mock_mgr = mock.MagicMock(__name__="Test")
        resource_classes = [mock.Mock()]
        task_id = "task_id"
        mock_name_matches_object.return_value = True

        consumer = manager.SeekAndDestroy(
            mock_mgr, None, None,
            resource_classes=resource_classes,
            task_id=task_id)._consumer

        admin = mock.MagicMock()
        user1 = {"id": "a", "tenant_id": "uuid1"}
        cache = {}

        consumer(cache, (admin, user1, "res"))
        mock_mgr.assert_called_once_with(
            resource="res",
            admin=mock__get_cached_client.return_value,
            user=mock__get_cached_client.return_value,
            tenant_uuid=user1["tenant_id"])
        mock__get_cached_client.assert_has_calls([
            mock.call(admin),
            mock.call(user1)
        ])
        mock__delete_single_resource.assert_called_once_with(
            mock_mgr.return_value)

        mock_mgr.reset_mock()
        mock__get_cached_client.reset_mock()
        mock__delete_single_resource.reset_mock()
        mock_name_matches_object.reset_mock()

        consumer(cache, (admin, None, "res2"))
        mock_mgr.assert_called_once_with(
            resource="res2",
            admin=mock__get_cached_client.return_value,
            user=mock__get_cached_client.return_value,
            tenant_uuid=None)

        mock__get_cached_client.assert_has_calls([
            mock.call(admin),
            mock.call(None)
        ])
        mock__delete_single_resource.assert_called_once_with(
            mock_mgr.return_value)

    @mock.patch("rally.common.utils.name_matches_object")
    @mock.patch("%s.SeekAndDestroy._get_cached_client" % BASE)
    @mock.patch("%s.SeekAndDestroy._delete_single_resource" % BASE)
    def test__consumer_with_noname_resource(self, mock__delete_single_resource,
                                            mock__get_cached_client,
                                            mock_name_matches_object):
        mock_mgr = mock.MagicMock(__name__="Test")
        mock_mgr.return_value.name.return_value = True
        task_id = "task_id"
        mock_name_matches_object.return_value = False

        consumer = manager.SeekAndDestroy(mock_mgr, None, None,
                                          task_id=task_id)._consumer

        consumer(None, (None, None, "res"))
        self.assertFalse(mock__delete_single_resource.called)

        mock_mgr.return_value.name.return_value = base.NoName("foo")
        consumer(None, (None, None, "res"))
        mock__delete_single_resource.assert_called_once_with(
            mock_mgr.return_value)

    @mock.patch("%s.broker.run" % BASE)
    def test_exterminate(self, mock_broker_run):
        manager_cls = mock.MagicMock(_threads=5)
        cleaner = manager.SeekAndDestroy(manager_cls, None, None)
        cleaner._publisher = mock.Mock()
        cleaner._consumer = mock.Mock()
        cleaner.exterminate()

        mock_broker_run.assert_called_once_with(cleaner._publisher,
                                                cleaner._consumer,
                                                consumers_count=5)


class ResourceManagerTestCase(test.TestCase):

    def _get_res_mock(self, **kw):
        _mock = mock.MagicMock()
        for k, v in kw.items():
            setattr(_mock, k, v)
        return _mock

    def _list_res_names_helper(self, names, admin_required, mock_iter):
        self.assertEqual(set(names),
                         manager.list_resource_names(admin_required))
        mock_iter.assert_called_once_with(base.ResourceManager)
        mock_iter.reset_mock()

    @mock.patch("%s.discover.itersubclasses" % BASE)
    def test_list_resource_names(self, mock_itersubclasses):
        mock_itersubclasses.return_value = [
            self._get_res_mock(_service="fake", _resource="1",
                               _admin_required=True),
            self._get_res_mock(_service="fake", _resource="2",
                               _admin_required=False),
            self._get_res_mock(_service="other", _resource="2",
                               _admin_required=False)
        ]

        self._list_res_names_helper(
            ["fake", "other", "fake.1", "fake.2", "other.2"],
            None, mock_itersubclasses)
        self._list_res_names_helper(
            ["fake", "fake.1"],
            True, mock_itersubclasses)
        self._list_res_names_helper(
            ["fake", "other", "fake.2", "other.2"],
            False, mock_itersubclasses)

    @mock.patch("%s.discover.itersubclasses" % BASE)
    def test_find_resource_managers(self, mock_itersubclasses):
        mock_itersubclasses.return_value = [
            self._get_res_mock(_service="fake", _resource="1", _order=1,
                               _admin_required=True),
            self._get_res_mock(_service="fake", _resource="2", _order=3,
                               _admin_required=False),
            self._get_res_mock(_service="other", _resource="2", _order=2,
                               _admin_required=False)
        ]

        self.assertEqual(mock_itersubclasses.return_value[0:2],
                         manager.find_resource_managers(names=["fake"]))

        self.assertEqual(mock_itersubclasses.return_value[0:1],
                         manager.find_resource_managers(names=["fake.1"]))

        self.assertEqual(
            [mock_itersubclasses.return_value[0],
             mock_itersubclasses.return_value[2],
             mock_itersubclasses.return_value[1]],
            manager.find_resource_managers(names=["fake", "other"]))

        self.assertEqual(mock_itersubclasses.return_value[0:1],
                         manager.find_resource_managers(names=["fake"],
                                                        admin_required=True))
        self.assertEqual(mock_itersubclasses.return_value[1:2],
                         manager.find_resource_managers(names=["fake"],
                                                        admin_required=False))

    @mock.patch("rally.common.plugin.discover.itersubclasses")
    @mock.patch("%s.SeekAndDestroy" % BASE)
    @mock.patch("%s.find_resource_managers" % BASE,
                return_value=[mock.MagicMock(), mock.MagicMock()])
    def test_cleanup(self, mock_find_resource_managers, mock_seek_and_destroy,
                     mock_itersubclasses):
        class A(utils.RandomNameGeneratorMixin):
            pass

        class B(object):
            pass

        mock_itersubclasses.return_value = [A, B]

        manager.cleanup(names=["a", "b"], admin_required=True,
                        admin="admin", users=["user"],
                        superclass=A,
                        task_id="task_id")

        mock_find_resource_managers.assert_called_once_with(["a", "b"], True)

        mock_seek_and_destroy.assert_has_calls([
            mock.call(mock_find_resource_managers.return_value[0], "admin",
                      ["user"], api_versions=None,
                      resource_classes=[A], task_id="task_id"),
            mock.call().exterminate(),
            mock.call(mock_find_resource_managers.return_value[1], "admin",
                      ["user"], api_versions=None,
                      resource_classes=[A], task_id="task_id"),
            mock.call().exterminate()
        ])

    @mock.patch("rally.common.plugin.discover.itersubclasses")
    @mock.patch("%s.SeekAndDestroy" % BASE)
    @mock.patch("%s.find_resource_managers" % BASE,
                return_value=[mock.MagicMock(), mock.MagicMock()])
    def test_cleanup_with_api_versions(self,
                                       mock_find_resource_managers,
                                       mock_seek_and_destroy,
                                       mock_itersubclasses):
        class A(utils.RandomNameGeneratorMixin):
            pass

        class B(object):
            pass

        mock_itersubclasses.return_value = [A, B]

        api_versions = {"cinder": {"version": "1", "service_type": "volume"}}
        manager.cleanup(names=["a", "b"], admin_required=True,
                        admin="admin", users=["user"],
                        api_versions=api_versions,
                        superclass=utils.RandomNameGeneratorMixin,
                        task_id="task_id")

        mock_find_resource_managers.assert_called_once_with(["a", "b"], True)

        mock_seek_and_destroy.assert_has_calls([
            mock.call(mock_find_resource_managers.return_value[0], "admin",
                      ["user"], api_versions=api_versions,
                      resource_classes=[A], task_id="task_id"),
            mock.call().exterminate(),
            mock.call(mock_find_resource_managers.return_value[1], "admin",
                      ["user"], api_versions=api_versions,
                      resource_classes=[A], task_id="task_id"),
            mock.call().exterminate()
        ])
