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
    """Represents task object."""

    def __init__(self, db_task=None):
        if db_task:
            self.task = db_task
        else:
            self.task = db.task_create({})

    @staticmethod
    def get_by_uuid(uuid):
        return Task(db.task_get_by_uuid(uuid))

    def update_status(self, status):
        db.task_update(self.task['uuid'], {'status': status})

    def set_failed(self):
        db.task_update(self.task['uuid'], {'failed': True})
