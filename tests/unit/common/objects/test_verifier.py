# Copyright 2016: Mirantis Inc.
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

from rally.common import objects
from rally import exceptions
from tests.unit import test


class VerifierTestCase(test.TestCase):
    def setUp(self):
        super(VerifierTestCase, self).setUp()

        self.db_obj = {"uuid": "uuid-1"}

    def test___str__(self):
        v = objects.Verifier(self.db_obj)
        self.db_obj["name"] = "name"
        self.db_obj["uuid"] = "uuid"
        self.assertEqual("'name' (UUID=uuid)", "%s" % v)

    def test_to_dict(self):
        v = objects.Verifier(self.db_obj)
        v._db_entry = mock.Mock()
        self.assertIsInstance(v.to_dict(), dict)

    @mock.patch("rally.common.objects.verifier.db.verifier_create")
    def test_init(self, mock_verifier_create):
        v = objects.Verifier(self.db_obj)
        self.assertEqual(0, mock_verifier_create.call_count)
        self.assertEqual(self.db_obj["uuid"], v.uuid)
        self.assertEqual(self.db_obj["uuid"], v["uuid"])

    @mock.patch("rally.common.objects.verifier.db.verifier_create")
    def test_create(self, mock_verifier_create):
        objects.Verifier.create("a", "b", "c", "d", "e", False)
        mock_verifier_create.assert_called_once_with(
            name="a", vtype="b", platform="c", source="d", version="e",
            system_wide=False, extra_settings=None)

    @mock.patch("rally.common.objects.verifier.db.verifier_get")
    def test_get(self, mock_verifier_get):
        mock_verifier_get.return_value = self.db_obj
        v = objects.Verifier.get(self.db_obj["uuid"])
        mock_verifier_get.assert_called_once_with(self.db_obj["uuid"])
        self.assertEqual(self.db_obj["uuid"], v.uuid)

    @mock.patch("rally.common.objects.verifier.db.verifier_list")
    def test_list(self, mock_verifier_list):
        mock_verifier_list.return_value = [self.db_obj]
        vs = objects.Verifier.list()
        mock_verifier_list.assert_called_once_with(None)
        self.assertEqual(self.db_obj["uuid"], vs[0].uuid)

    @mock.patch("rally.common.objects.verifier.db.verifier_delete")
    def test_delete(self, mock_verifier_delete):
        objects.Verifier.delete(self.db_obj["uuid"])
        mock_verifier_delete.assert_called_once_with(self.db_obj["uuid"])

    @mock.patch("rally.common.objects.verifier.db.verifier_update")
    def test_update_status(self, mock_verifier_update):
        v = objects.Verifier(self.db_obj)
        v.update_status(status="some-status")
        mock_verifier_update.assert_called_once_with(self.db_obj["uuid"],
                                                     status="some-status")

    @mock.patch("rally.env.env_mgr.EnvManager.get")
    def test_env_and_deployment_properties(self, mock_env_manager_get):
        v = objects.Verifier(self.db_obj)
        v.set_env("some-env")
        self.assertEqual(mock_env_manager_get.return_value,
                         v.deployment.env_obj)
        self.assertEqual(mock_env_manager_get.return_value,
                         v.env)
        mock_env_manager_get.assert_called_once_with("some-env")

    def test_deployment_property_raise_exc(self):
        v = objects.Verifier(self.db_obj)
        self.assertRaises(exceptions.RallyException, getattr, v, "deployment")

    @mock.patch("rally.common.objects.verifier.manager")
    def test_manager_property(self, mock_manager):
        self.db_obj["type"] = "some"
        self.db_obj["platform"] = "platform"
        v = objects.Verifier(self.db_obj)
        self.assertIsNone(v._manager)
        self.assertFalse(mock_manager.VerifierManager.get.called)

        self.assertEqual(
            mock_manager.VerifierManager.get.return_value.return_value,
            v.manager)
        mock_manager.VerifierManager.get.assert_called_once_with(
            self.db_obj["type"], self.db_obj["platform"])
