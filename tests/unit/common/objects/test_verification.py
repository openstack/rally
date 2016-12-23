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
from rally import consts
from tests.unit import test


class VerificationTestCase(test.TestCase):
    def setUp(self):
        super(VerificationTestCase, self).setUp()

        self.db_obj = {"uuid": "uuid-1"}

    @mock.patch("rally.common.objects.verification.db.verification_create")
    def test_init(self, mock_verification_create):
        v = objects.Verification(self.db_obj)
        self.assertEqual(0, mock_verification_create.call_count)
        self.assertEqual(self.db_obj["uuid"], v.uuid)
        self.assertEqual(self.db_obj["uuid"], v["uuid"])

    @mock.patch("rally.common.objects.verification.db.verification_create")
    def test_create(self, mock_verification_create):
        objects.Verification.create("some-verifier", "some-deployment", {})
        mock_verification_create.assert_called_once_with("some-verifier",
                                                         "some-deployment", {})

    @mock.patch("rally.common.objects.verification.db.verification_get")
    def test_get(self, mock_verification_get):
        mock_verification_get.return_value = self.db_obj
        v = objects.Verification.get(self.db_obj["uuid"])
        mock_verification_get.assert_called_once_with(self.db_obj["uuid"])
        self.assertEqual(self.db_obj["uuid"], v.uuid)

    @mock.patch("rally.common.objects.verification.db.verification_list")
    def test_list(self, mock_verification_list):
        mock_verification_list.return_value = [self.db_obj]
        vs = objects.Verification.list()
        mock_verification_list.assert_called_once_with(None, None, None)
        self.assertEqual(self.db_obj["uuid"], vs[0].uuid)

    @mock.patch("rally.common.objects.verification.db.verification_delete")
    def test_delete(self, mock_verification_delete):
        objects.Verification(self.db_obj).delete()
        mock_verification_delete.assert_called_once_with(self.db_obj["uuid"])

    @mock.patch("rally.common.objects.verification.db.verification_update")
    def test_update_status(self, mock_verification_update):
        v = objects.Verification(self.db_obj)
        v.update_status(status="some-status")
        mock_verification_update.assert_called_once_with(self.db_obj["uuid"],
                                                         status="some-status")

    @mock.patch("rally.common.objects.verification.db.verification_update")
    def test_finish(self, mock_verification_update):
        v = objects.Verification(self.db_obj)
        totals = {
            "tests_count": 2,
            "tests_duration": "0.54",
            "success": 2,
            "skip": 0,
            "expected_failures": 0,
            "unexpected_success": 0,
            "failures": 0
        }
        tests = {
            "foo_test[gate,negative]": {
                "name": "foo_test",
                "duration": "0.25",
                "status": "success",
                "tags": ["gate", "negative"]
            },
            "bar_test[gate,negative]": {
                "name": "bar.Test",
                "duration": "0.29",
                "status": "success",
                "tags": ["gate", "negative"]
            }
        }
        v.finish(totals, tests)
        mock_verification_update.assert_called_once_with(
            self.db_obj["uuid"], status=consts.VerificationStatus.FINISHED,
            tests=tests, **totals)

    @mock.patch("rally.common.objects.verification.db.verification_update")
    def test_set_error(self, mock_verification_update):
        v = objects.Verification(self.db_obj)
        v.set_error("Some error")
        mock_verification_update.assert_called_once_with(
            self.db_obj["uuid"], status=consts.VerificationStatus.FAILED)
