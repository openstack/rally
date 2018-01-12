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


class Verification(object):
    """Represents a verification object."""
    TIME_FORMAT = consts.TimeFormat.ISO8601

    def __init__(self, verification):
        """Init a verification object.

        :param verification: Dict representation of a verification
                             in the database
        """
        self._db_entry = verification
        self._db_entry["deployment_uuid"] = self._db_entry["env_uuid"]

    def __getattr__(self, attr):
        return self._db_entry[attr]

    def __getitem__(self, item):
        return self._db_entry[item]

    def to_dict(self, item=None):
        data = {}
        formatters = ["created_at", "updated_at"]
        fields = ["deployment_uuid", "env_uuid", "verifier_uuid", "uuid", "id",
                  "unexpected_success", "status", "tests", "skipped",
                  "tags", "tests_duration", "run_args", "success",
                  "expected_failures", "tests_count", "failures"]
        for field in fields:
            data[field] = self._db_entry.get(field, "")
        for field in formatters:
            data[field] = self._db_entry.get(field, "").strftime(
                self.TIME_FORMAT)
        return data

    @classmethod
    def create(cls, verifier_id, deployment_id, tags=None, run_args=None):
        return cls(db.verification_create(
            verifier_id, deployment_id, tags, run_args))

    @classmethod
    def get(cls, verification_uuid):
        return cls(db.verification_get(verification_uuid))

    @classmethod
    def list(cls, verifier_id=None, deployment_id=None, tags=None,
             status=None):
        verification_list = db.verification_list(verifier_id, deployment_id,
                                                 tags, status)
        return [cls(db_entry) for db_entry in verification_list]

    def delete(self):
        db.verification_delete(self.uuid)

    def _update(self, **properties):
        self._db_entry = db.verification_update(self.uuid, **properties)

    def update_status(self, status):
        self._update(status=status)

    def finish(self, totals, tests):
        if (totals.get("failures", 0) == 0 and
                totals.get("unexpected_success", 0) == 0):
            status = consts.VerificationStatus.FINISHED
        else:
            status = consts.VerificationStatus.FAILED
        self._update(status=status, tests=tests, **totals)

    def set_error(self, error_message):
        # TODO(andreykurilin): Save error message in the database.
        self.update_status(consts.VerificationStatus.CRASHED)
