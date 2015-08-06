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
        self._update(status=consts.TaskStatus.FINISHED, **total)

        # create db object for results
        data = total.copy()
        data["test_cases"] = test_cases
        db.verification_result_create(self.uuid, data)

    def get_results(self):
        try:
            return db.verification_result_get(self.uuid)
        except exceptions.NotFoundException:
            return None
