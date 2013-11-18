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

from rally import db


class Task(object):
    """Represents a task object."""

    def __init__(self, task=None, **attributes):
        if task:
            self.task = task
        else:
            self.task = db.task_create(attributes)

    def __getitem__(self, key):
            return self.task[key]

    @staticmethod
    def get(uuid):
        return Task(db.task_get(uuid))

    @staticmethod
    def delete_by_uuid(uuid, status=None):
        db.task_delete(uuid, status=status)

    def _update(self, values):
        self.task = db.task_update(self.task['uuid'], values)

    def update_status(self, status):
        self._update({'status': status})

    def update_verification_log(self, log):
        self._update({'verification_log': log})

    def set_failed(self):
        self._update({'failed': True})

    def append_results(self, key, value):
        db.task_result_create(self.task['uuid'], key, value)

    def delete(self, status=None):
        db.task_delete(self.task['uuid'], status=status)
