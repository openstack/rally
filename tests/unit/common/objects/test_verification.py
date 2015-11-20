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

from rally.common import objects
from tests.unit import test
from tests.unit.verification import fakes


class VerificationTestCase(test.TestCase):
    def setUp(self):
        super(VerificationTestCase, self).setUp()
        self.db_obj = {
            "id": 777,
            "uuid": "test_uuid",
            "failures": 0, "tests": 2, "errors": 0, "time": "0.54",
            "expected_failures": 0,
            "details": {
                "failures": 0, "tests": 2, "errors": 0, "time": "0.54",
                "expected_failures": 0,
                "test_cases": [
                    {"classname": "foo.Test",
                     "name": "foo_test[gate,negative]",
                     "time": "0.25"},
                    {"classname": "bar.Test",
                     "name": "bar_test[gate,negative]",
                     "time": "0.29"}]}}

    @mock.patch("rally.common.objects.verification.db.verification_create")
    def test_init_with_create(self, mock_verification_create):
        objects.Verification(deployment_uuid="some_deployment_uuid")
        mock_verification_create.assert_called_once_with(
            "some_deployment_uuid")

    @mock.patch("rally.common.objects.verification.db.verification_create")
    def test_init_without_create(self, mock_verification_create):
        verification = objects.Verification(db_object=self.db_obj)

        self.assertEqual(0, mock_verification_create.call_count)
        self.assertEqual(self.db_obj["failures"], verification.failures)
        self.assertEqual(self.db_obj["tests"], verification.tests)
        self.assertEqual(self.db_obj["errors"], verification.errors)
        self.assertEqual(self.db_obj["time"], verification.time)

    @mock.patch("rally.common.objects.verification.db.verification_get")
    def test_get(self, mock_verification_get):
        objects.Verification.get(self.db_obj["id"])
        mock_verification_get.assert_called_once_with(self.db_obj["id"])

    @mock.patch("rally.common.objects.verification.db.verification_list")
    def test_list(self, mock_verification_list):
        objects.Verification.list()
        mock_verification_list.assert_called_once_with(None)

    @mock.patch("rally.common.objects.verification.db.verification_delete")
    @mock.patch("rally.common.objects.verification.db.verification_create")
    def test_create_and_delete(self, mock_verification_create,
                               mock_verification_delete):
        verification = objects.Verification(db_object=self.db_obj)
        verification.delete()
        mock_verification_delete.assert_called_once_with(self.db_obj["uuid"])

    @mock.patch("rally.common.objects.verification.db.verification_update")
    def test_set_failed(self, mock_verification_update):
        mock_verification_update.return_value = self.db_obj
        verification = objects.Verification(db_object=self.db_obj)
        verification.set_failed()
        mock_verification_update.assert_called_once_with(
            self.db_obj["uuid"], {"status": "failed"})

    @mock.patch(
        ("rally.common.objects.verification.db.verification_result_create"))
    @mock.patch("rally.common.objects.verification.db.verification_update")
    def test_finish_verification(self, mock_verification_update,
                                 mock_verification_result_create):
        verification = objects.Verification(db_object=self.db_obj)
        fake_results = fakes.get_fake_test_case()
        verification.finish_verification(
            fake_results["total"],
            fake_results["test_cases"])

        expected_values = {"status": "finished"}
        expected_values.update(fake_results["total"])
        # expected_failures should be merged with failures
        expected_values.pop("expected_failures")
        mock_verification_update.assert_called_with(
            self.db_obj["uuid"], expected_values)

        expected_data = fake_results["total"].copy()
        expected_data["test_cases"] = fake_results["test_cases"]
        mock_verification_result_create.assert_called_once_with(
            verification.uuid, expected_data)
