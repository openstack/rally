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

from rally.common import db
from rally import consts
from rally import exceptions


_MAP_OLD_TO_NEW_STATUSES = {
    "OK": "success",
    "FAIL": "fail",
    "SKIP": "skip"
}


class Verification(object):
    """Represents results of verification."""

    def __init__(self, db_object=None, deployment_uuid=None):
        if db_object:
            self.db_object = db_object
        else:
            self.db_object = db.verification_create(deployment_uuid)

    def __getattr__(self, item):
        return self.db_object[item]

    def __getitem__(self, key):
        return self.db_object[key]

    @classmethod
    def get(cls, uuid):
        return cls(db.verification_get(uuid))

    @classmethod
    def list(cls, status=None):
        return db.verification_list(status)

    def delete(self):
        db.verification_delete(self.db_object["uuid"])

    def _update(self, **values):
        self.db_object = db.verification_update(self.uuid, values)

    def update_status(self, status):
        self._update(status=status)

    def start_verifying(self, set_name):
        self._update(status=consts.TaskStatus.VERIFYING, set_name=set_name)

    def set_failed(self):
        self.update_status(consts.TaskStatus.FAILED)

    def set_running(self):
        self.update_status(consts.TaskStatus.RUNNING)

    def finish_verification(self, total, test_cases):
        # update verification db object
        self._update(status=consts.TaskStatus.FINISHED,
                     tests=total["tests"],
                     # Expected failures are still failures, so we should
                     # merge them together in main info of Verification
                     # (see db model for Verification for more details)
                     failures=(total["failures"] + total["expected_failures"]),
                     time=total["time"])

        # create db object for results
        data = total.copy()
        data["test_cases"] = test_cases
        db.verification_result_create(self.uuid, data)

    def get_results(self):
        try:
            results = db.verification_result_get(self.uuid)["data"]
        except exceptions.NotFoundException:
            return None

        if "errors" in results:
            # NOTE(andreykurilin): there is no "error" status in verification
            # and this key presents only in old format, so it can be used as
            # an identifier for old format.
            for test in results["test_cases"].keys():
                old_status = results["test_cases"][test]["status"]
                new_status = _MAP_OLD_TO_NEW_STATUSES.get(old_status,
                                                          old_status.lower())
                results["test_cases"][test]["status"] = new_status

                if "failure" in results["test_cases"][test]:
                    results["test_cases"][test]["traceback"] = results[
                        "test_cases"][test]["failure"]["log"]
                    results["test_cases"][test].pop("failure")
            results["unexpected_success"] = 0
            results["expected_failures"] = 0
        return results
