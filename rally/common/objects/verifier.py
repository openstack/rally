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

from rally.common import db
from rally import consts
from rally import exceptions
from rally.verification import manager


class Verifier(object):
    """Represents a verifier object."""
    TIME_FORMAT = consts.TimeFormat.ISO8601

    def __init__(self, verifier):
        """Init a verifier object.

        :param verifier: Dict representation of a verifier in the database
        """
        self._db_entry = verifier

        self._deployment = None
        self._manager = None

    def __getattr__(self, attr):
        return self._db_entry[attr]

    def __getitem__(self, item):
        return self._db_entry[item]

    def __str__(self):
        return "'%s' (UUID=%s)" % (self.name, self.uuid)

    def to_dict(self, item=None):
        data = {}
        formatters = ["created_at", "updated_at"]
        fields = ["status", "system_wide", "uuid", "type", "platform",
                  "name", "source", "version", "extra_settings",
                  "id", "description"]
        for field in fields:
            data[field] = self._db_entry.get(field, "")
        for field in formatters:
            data[field] = self._db_entry.get(field, "").strftime(
                self.TIME_FORMAT)
        return data

    @classmethod
    def create(cls, name, vtype, platform, source, version, system_wide,
               extra_settings=None):
        db_entry = db.verifier_create(name=name, vtype=vtype,
                                      platform=platform, source=source,
                                      version=version, system_wide=system_wide,
                                      extra_settings=extra_settings)
        return cls(db_entry)

    @classmethod
    def get(cls, verifier_id):
        return cls(db.verifier_get(verifier_id))

    @classmethod
    def list(cls, status=None):
        return [cls(db_entry) for db_entry in db.verifier_list(status)]

    @staticmethod
    def delete(verifier_id):
        db.verifier_delete(verifier_id)

    def update_status(self, status):
        self.update_properties(status=status)

    def update_properties(self, **properties):
        self._db_entry = db.verifier_update(self.uuid, **properties)

    def set_env(self, env_id):
        from rally.common import objects
        self._deployment = objects.Deployment.get(env_id)

    @property
    def deployment(self):
        # TODO(andreykurilin): deprecate this property someday
        if self._deployment is None:
            raise exceptions.RallyException(
                "Verifier is not linked to any deployment. Please, call "
                "`set_env` method.")
        return self._deployment

    @property
    def env(self):
        return self.deployment.env_obj

    @property
    def manager(self):
        # lazy load manager to be able to use non-plugin related stuff without
        # loading plugins
        if not self._manager:
            self._manager = manager.VerifierManager.get(
                self.type, self.platform)(self)
        return self._manager
