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

import datetime as dt

import jsonschema

from rally.common.i18n import _, _LW
from rally.common import db
from rally.common import logging
from rally import consts
from rally import exceptions


LOG = logging.getLogger(__name__)

CREDENTIALS_SCHEMA = {
    "type": "object",
    "patternProperties": {
        ".*": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "admin": {"type": "object"},
                    "users": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["admin", "users"],
                "additionalProperties": False,
            },
        }
    },
    "minProperties": 1,
}


class Deployment(object):
    """Represents a deployment object."""

    def __init__(self, deployment=None, **attributes):
        if deployment:
            self.deployment = deployment
        else:
            self.deployment = db.deployment_create(attributes)

    def __getitem__(self, key):
        # TODO(astudenov): remove this in future releases
        if key == "admin" or key == "users":
            LOG.warning(_LW("deployment.%s is deprecated in Rally 0.9.0. "
                            "Use deployment.get_credentials_for('openstack')"
                            "['%s'] to get credentials.") % (key, key))
            return self.get_credentials_for("openstack")[key]
        return self.deployment[key]

    @staticmethod
    def get(deploy):
        return Deployment(db.deployment_get(deploy))

    @staticmethod
    def list(status=None, parent_uuid=None, name=None):
        return db.deployment_list(status, parent_uuid, name)

    @staticmethod
    def delete_by_uuid(uuid):
        db.deployment_delete(uuid)

    def _update(self, values):
        self.deployment = db.deployment_update(self.deployment["uuid"], values)

    def update_status(self, status):
        self._update({"status": status})

    def update_name(self, name):
        self._update({"name": name})

    def update_config(self, config):
        self._update({"config": config})

    def update_credentials(self, credentials):
        jsonschema.validate(credentials, CREDENTIALS_SCHEMA)
        self._update({"credentials": credentials})

    def get_credentials_for(self, namespace):
        try:
            return self.deployment["credentials"][namespace][0]
        except (KeyError, IndexError) as e:
            LOG.exception(e)
            raise exceptions.RallyException(_(
                "No credentials found for %s") % namespace)

    def set_started(self):
        self._update({"started_at": dt.datetime.now(),
                      "status": consts.DeployStatus.DEPLOY_STARTED})

    def set_completed(self):
        self._update({"completed_at": dt.datetime.now(),
                      "status": consts.DeployStatus.DEPLOY_FINISHED})

    def add_resource(self, provider_name, type=None, info=None):
        return db.resource_create({
            "deployment_uuid": self.deployment["uuid"],
            "provider_name": provider_name,
            "type": type,
            "info": info,
        })

    def get_resources(self, provider_name=None, type=None):
        return db.resource_get_all(self.deployment["uuid"],
                                   provider_name=provider_name, type=type)

    @staticmethod
    def delete_resource(resource_id):
        db.resource_delete(resource_id)

    def delete(self):
        db.deployment_delete(self.deployment["uuid"])
