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

from rally.common import logging
from rally import consts
from rally.env import env_mgr
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
                    "admin": {"type": ["object", "null"]},
                    "users": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                },
                "required": ["admin", "users"],
                "additionalProperties": False,
            },
        }
    }
}


_STATUS_OLD_TO_NEW = {
    consts.DeployStatus.DEPLOY_INIT: env_mgr.STATUS.INIT,
    consts.DeployStatus.DEPLOY_STARTED: env_mgr.STATUS.INIT,
    consts.DeployStatus.DEPLOY_FINISHED: env_mgr.STATUS.READY,
    consts.DeployStatus.DEPLOY_FAILED: env_mgr.STATUS.FAILED_TO_CREATE,
    consts.DeployStatus.DEPLOY_INCONSISTENT: env_mgr.STATUS.FAILED_TO_CREATE,
    consts.DeployStatus.DEPLOY_SUBDEPLOY: env_mgr.STATUS.INIT,
    consts.DeployStatus.CLEANUP_STARTED: env_mgr.STATUS.CLEANING,
    consts.DeployStatus.CLEANUP_FAILED: env_mgr.STATUS.READY,
    consts.DeployStatus.CLEANUP_FINISHED: env_mgr.STATUS.READY
}
_STATUS_NEW_TO_OLD = {
    env_mgr.STATUS.INIT: consts.DeployStatus.DEPLOY_INIT,
    env_mgr.STATUS.READY: consts.DeployStatus.DEPLOY_FINISHED,
    env_mgr.STATUS.FAILED_TO_CREATE: consts.DeployStatus.DEPLOY_FAILED,
    env_mgr.STATUS.CLEANING: consts.DeployStatus.CLEANUP_STARTED,
    env_mgr.STATUS.DESTROYING: consts.DeployStatus.DEPLOY_INIT,
    env_mgr.STATUS.FAILED_TO_DESTROY: consts.DeployStatus.DEPLOY_INCONSISTENT,
    env_mgr.STATUS.DESTROYED: consts.DeployStatus.DEPLOY_INIT
}


class Deployment(object):
    """Represents a deployment object."""
    TIME_FORMAT = consts.TimeFormat.ISO8601

    def __init__(self, deployment=None, name=None, config=None, extras=None):
        if deployment:
            self._env = deployment
        else:
            self._env = env_mgr.EnvManager.create(
                name=name,
                spec=config or {},
                description="",
                extras=extras or {})
        self._env_data = self._env.data
        self._all_credentials = {}
        for p in self._env_data["platforms"].values():
            self._all_credentials[p["platform_name"]] = [p["platform_data"]]

        self.config = {}
        for p_name, p_cfg in self._env_data["spec"].items():
            if p_name.startswith("existing@"):
                p_name = p_name[9:]
            self.config[p_name] = p_cfg

    @property
    def env_obj(self):
        return self._env

    def __getitem__(self, key):
        if key == "status":
            status = self._env.status
            return _STATUS_NEW_TO_OLD.get(status, status)
        elif key == "extra":
            return self._env_data["extras"]
        if hasattr(self._env, key):
            return getattr(self._env, key)
        elif hasattr(self, key):
            return getattr(self, key)
        return self._env_data[key]

    def to_dict(self):
        return {
            "uuid": self._env_data["uuid"],
            "parent_uuid": None,
            "name": self._env_data["name"],
            "created_at": self._env_data["created_at"],
            "started_at": self._env_data["created_at"],
            "completed_at": "n/a",
            "updated_at": self._env_data["updated_at"],
            "config": self.config,
            "credentials": self._all_credentials,
            "status": self["status"]
        }

    @staticmethod
    def get(deploy):
        return Deployment(env_mgr.EnvManager.get(deploy))

    @staticmethod
    def list(status=None, parent_uuid=None, name=None):
        # we do not use parent_uuid...
        if name:
            try:
                env = env_mgr.EnvManager(name)
            except exceptions.DBRecordNotFound:
                return []
            envs = [env]
        else:
            envs = env_mgr.EnvManager.list(status=status)

        return [Deployment(e) for e in envs]

    def get_validation_context(self):
        return self._env.get_validation_context()

    def verify_connections(self):
        for platform_name, result in self._env.check_health().items():
            if not result["available"]:
                raise exceptions.RallyException(
                    "Platform %s is not available: %s." % (platform_name,
                                                           result["message"]))

    def get_platforms(self):
        return self._all_credentials.keys()

    def get_all_credentials(self):
        all_credentials = {}
        for platform, credentials in self._all_credentials.items():
            if platform == "openstack":
                try:
                    from rally_openstack import credential
                except ImportError:
                    all_credentials[platform] = credentials
                else:
                    admin = credentials[0]["admin"]
                    if admin:
                        admin = credential.OpenStackCredential(
                            permission=consts.EndpointPermission.ADMIN,
                            **admin)
                    all_credentials[platform] = [{
                        "admin": admin,
                        "users": [credential.OpenStackCredential(**user)
                                  for user in credentials[0]["users"]]}]
            else:
                all_credentials[platform] = credentials
        return all_credentials

    def get_credentials_for(self, platform):
        if platform == "default":
            return {"admin": None, "users": []}

        creds = self.get_all_credentials()
        try:
            return creds[platform][0]
        except (KeyError, IndexError):
            raise exceptions.RallyException(
                "No credentials found for %s" % platform)
