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

import copy
import sys

import jsonschema

from rally.common import db
from rally.common import logging
from rally.common import utils
from rally.env import platform
from rally import exceptions


LOG = logging.getLogger(__name__)


class _EnvStatus(utils.ImmutableMixin, utils.EnumMixin):
    """Rally Env Statuses."""

    INIT = "INITIALIZING"

    READY = "READY"
    FAILED_TO_CREATE = "FAILED TO CREATE"

    CLEANING = "CLEANING"

    DESTROYING = "DESTROYING"
    FAILED_TO_DESTROY = "FAILED TO DESTROY"
    DESTROYED = "DESTROYED"

    TRANSITION_TABLE = {
        INIT: (READY, FAILED_TO_CREATE),
        READY: (DESTROYING, CLEANING),
        CLEANING: (READY, ),
        FAILED_TO_CREATE: (DESTROYING, ),
        DESTROYING: (DESTROYED, FAILED_TO_DESTROY),
        FAILED_TO_DESTROY: (DESTROYING, )
    }


STATUS = _EnvStatus()


class EnvManager(object):
    """Implements life cycle management of Rally Envs.


    EnvManager is one of key Rally components,
    It manages and stores information about tested platforms. Every Env has:
    - unique name and UUID
    - dates when it was created and updated
    - platform plugins spec and data
    - platform data


    Env Input has next syntax:

    {
        "type": "object",
        "properties": {
            "version": {
                "type": "integer",
                "description": "Env version"
            },
            "description": {
                "type": "string",
                "description": "User specific description of deployment"
            },
            "extras": {
                "type": "object",
                "description": "Custom dict with  data"
            },
            "config": {
                "type": "object",
                "properties": {
                    "*": {
                        "type": "object",
                        "*": {},
                        "description": |
                            Keys are option's name, values are option's values
                    },
                    "description": "Keys are groups, values are options names"
                }
            },
            "platforms": {
                "type": "object",
                "properties": {
                    "*": {
                        "type": "object",
                        "description": |
                            Key is platform plugin name,
                            values are plugin arguments
                    }
                }
            }
        }
    }

    Env.data property is dict that is consumed by other rally components,
    like task, verify and maybe something else in future.

    {
        "name": {"type": "string"},
        "status": {"type": "string"},
        "description: {"type": "string"},
        "extras": {"type": "object"},
        "config": {"type": "object"},
        "platforms": {
            "type": "object",
            "*": {
                "type": "object"
                "description": "Key is platform name, value is platform data"
            }
        }
    }
    """

    def __init__(self, _data):
        """Private method to initializes env manager.

        THis method is not meant to be called directly, use one of
        next class methods: get(), create() or list().
        """
        self._env = _data
        self.uuid = self._env["uuid"]

    @property
    def status(self):
        """Returns current state of Env that was fetched from DB."""
        return db.env_get_status(self.uuid)

    @property
    def data(self):
        """Returns full information about env including platforms."""
        self._env = db.env_get(self.uuid)
        return {
            "id": self._env["id"],
            "uuid": self._env["uuid"],
            "created_at": self._env["created_at"],
            "updated_at": self._env["updated_at"],
            "name": self._env["name"],
            "description": self._env["description"],
            "status": self._env["status"],
            "spec": copy.deepcopy(self._env["spec"]),
            "extras": copy.deepcopy(self._env["extras"]),
            "platforms": db.platforms_list(self.uuid)
        }

    def _get_platforms(self):
        """Iterate over Envs platforms.

        :returns: Generator that returns list of tuples
                  (uuid, instance of rally.env.platform.Platform)
        """
        raw_platforms = db.platforms_list(self.uuid)
        platforms = []

        for p in raw_platforms:
            plugin_cls = platform.Platform.get(p["plugin_name"])
            platforms.append(
                plugin_cls(
                    p["plugin_spec"],
                    uuid=p["uuid"],
                    plugin_data=p["plugin_data"],
                    platform_data=p["platform_data"],
                    status=p["status"]
                )
            )

        return platforms

    @classmethod
    def get(cls, uuid_or_name):
        """Get the instance of EnvManager by uuid or name.

        :param uuid_or_name: Returns record that has uuid or name equal to it.
        :returns: Instance of rally.env.env_mgr.EnvManager
        """
        return cls(db.env_get(uuid_or_name))

    @classmethod
    def list(cls, status=None):
        """Returns list of instances of EnvManagers."""
        return [cls(data) for data in db.env_list(status=status)]

    @classmethod
    def _validate_and_create_env(cls, name, description, extras, spec):
        """Validated and create env and platforms DB records.

        Do NOT use this method directly. Call create() method instead.

        - Restore full name of plugin. If only platform name is specified
        plugin with name existing@<platform_name> is going to be used
        - Validates spec using standard plugin validation mechanism
        - Creates env and platforms DB records in DB

        :returns: dict that contains env record stored in DB
        """
        for p_name, p_spec in spec.items():
            if "@" not in p_name:
                spec["existing@%s" % p_name] = p_spec
                spec.pop(p_name)

        errors = []
        for p_name, p_spec in spec.items():
            errors.extend(platform.Platform.validate(p_name, {}, spec, p_spec))
        if errors:
            raise exceptions.ManagerInvalidSpec(
                mgr="Env", spec=spec, errors=errors)

        _platforms = []
        for p_name, p_spec in spec.items():
            _platforms.append({
                "status": platform.STATUS.INIT,
                "plugin_name": p_name,
                "plugin_spec": p_spec,
                "platform_name": p_name.split("@")[1]
            })

        return cls(db.env_create(name, STATUS.INIT, description, extras,
                                 spec, _platforms))

    def _create_platforms(self):
        """Iterates over platform and creates them, storing results in DB.

        Do NOT use this method directly! Use create() instead.

        All platform statuses are going to be updated.
        - If everything is OK all platforms and env would have READY statuts.
        - If some of platforms failed, it will get status "FAILED TO CREATE"
          as well as Env, all following platforms would have "SKIPPED" state.
        - If there are issues with DB, and we can't store results to DB,
          platform will be destroyed so we won't keep messy env, everything
          will be logged.

        This is not ideal solution, but it's best that we can do at the moment
        """
        new_env_status = STATUS.READY

        for p in self._get_platforms():
            if new_env_status != STATUS.READY:
                db.platform_set_status(
                    p.uuid, platform.STATUS.INIT, platform.STATUS.SKIPPED)
                continue

            try:
                platform_data, plugin_data = p.create()
            except Exception:
                new_env_status = STATUS.FAILED_TO_CREATE
                LOG.exception(
                    "Failed to create platform (%(uuid)s): "
                    "%(name)s with spec: %(spec)s" %
                    {"uuid": p.uuid, "name": p.get_fullname(), "spec": p.spec})
                try:
                    db.platform_set_status(p.uuid, platform.STATUS.INIT,
                                           platform.STATUS.FAILED_TO_CREATE)
                except Exception:
                    LOG.Exception(
                        "Failed to set platform %(uuid)s status %(status)s"
                        % {"uuid": p.uuid,
                           "status": platform.STATUS.FAILED_TO_CREATE})

            if new_env_status == STATUS.FAILED_TO_CREATE:
                continue

            try:
                db.platform_set_data(
                    p.uuid,
                    platform_data=platform_data, plugin_data=plugin_data)
                db.platform_set_status(
                    p.uuid, platform.STATUS.INIT, platform.STATUS.READY)
            except Exception:
                new_env_status = STATUS.FAILED_TO_CREATE

                # NOTE(boris-42): We can't store platform data, because of
                #                 issues with DB, to keep env clean we must
                #                 destroy platform while we have complete data.
                p.status = platform.STATUS.FAILED_TO_CREATE
                p.platform_data, p.plugin_data = platform_data, plugin_data
                try:
                    p.destroy()
                    LOG.warrning("Couldn't store platform %s data to DB."
                                 "Attempt to destroy it succeeded." % p.uuid)
                except Exception:
                    LOG.exception(
                        "Couldn't store data of platform(%(uuid)s): %(name)s  "
                        "with spec: %(spec)s. Attempt to destroy it failed. "
                        "Sorry, but we can't do anything else for you. :("
                        % {"uuid": p.uuid,
                           "name": p.get_fullname(),
                           "spec": p.spec})

        db.env_set_status(self.uuid, STATUS.INIT, new_env_status)

    @classmethod
    def create(cls, name, description, extras, spec):
        """Creates DB record for new env and returns instance of Env class.

        :param name: User specified name of env
        :param description: User specified description
        :param extras: User specified dict with extra options
        :param spec: Specification that contains info about all
                     platform plugins and their arguments.
        :returns: EnvManager instance corresponding to created Env
        """
        self = cls._validate_and_create_env(name, description, extras, spec)
        self._create_platforms()
        return self

    def rename(self, new_name):
        """Renames env record.

        :param new_name: New Env name.
        """
        if self._env["name"] == new_name:
            return True
        return db.env_rename(self.uuid, self._env["name"], new_name)

    def update(self, description=None, extras=None):
        """Update description and extras for environment.

        :param description: New description for env
        :param extras: New extras for env
        """
        values = {}

        if description and description != self._env["description"]:
            values["description"] = description
        if extras and extras != self._env["extras"]:
            values["extras"] = extras

        if values:
            return db.env_update(self.uuid, **values)
        return True

    def update_spec(self, new_spec):
        """Update env spec. [not implemented]"""
        # NOTE(boris-42): This functionality requires proper implementation of
        #                 state machine  and journal execution, which we are
        #                 going to implement later for all code base
        raise NotImplementedError()

    _HEALTH_FORMAT = {
        "type": "object",
        "properties": {
            "available": {"type": "boolean"},
            "message": {"type": "string"},
            "traceback": {"type": "array", "minItems": 3, "maxItems": 3}
        },
        "required": ["available"],
        "additionalProperties": False
    }

    def check_health(self):
        """Iterates over all platforms in env and returns their health.

        Format of result is
        {
            "platform_name": {
                "available": True/False,
                "message": "custom message"},
                "traceback": ...
        }

        :return: Dict with results
        """
        result = {}

        for p in self._get_platforms():
            try:
                check_result = p.check_health()
                jsonschema.validate(check_result, self._HEALTH_FORMAT)
                check_result.setdefault("message", "OK!")
            except Exception as e:
                msg = ("Plugin %s.check_health() method is broken"
                       % p.get_fullname())
                LOG.exception(msg)
                check_result = {"message": msg, "available": False}
                if not isinstance(e, jsonschema.ValidationError):
                    check_result["traceback"] = sys.exc_info()

            result[p.get_fullname()] = check_result

        return result

    _INFO_FORMAT = {
        "type": "object",
        "properties": {
            "info": {},
            "error": {"type": "string"},
            "traceback": {"type": "array", "minItems": 3, "maxItems": 3},
        },
        "required": ["info"],
        "additionalProperties": False
    }

    def get_info(self):
        """Get detailed information about all platforms.

        Platform plugins may collect any information from plugin and return
        it back as a dict.
        """
        result = {}

        for p in self._get_platforms():
            try:
                info = p.info()
                jsonschema.validate(info, self._INFO_FORMAT)
            except Exception as e:
                msg = "Plugin %s.info() method is broken" % p.get_fullname()
                LOG.exception(msg)
                info = {"info": None, "error": msg}
                if not isinstance(e, jsonschema.ValidationError):
                    info["traceback"] = sys.exc_info()

            result[p.get_fullname()] = info

        return result

    _CLEANUP_FORMAT = {
        "type": "object",
        "properties": {
            "discovered": {"type": "integer"},
            "deleted": {"type": "integer"},
            "failed": {"type": "integer"},
            "resources": {
                "*": {
                    "type": "object",
                    "properties": {
                        "discovered": {"type": "integer"},
                        "deleted": {"type": "integer"},
                        "failed": {"type": "integer"}
                    },
                    "required": ["discovered", "deleted", "failed"],
                    "additionalProperties": False
                }
            },
            "errors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "resource_id": {"type": "string"},
                        "resource_type": {"type": "string"},
                        "message": {"type": "string"},
                        "traceback": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3
                        }
                    },
                    "required": ["message"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["discovered", "deleted", "failed", "resources", "errors"],
        "additionalProperties": False
    }

    def cleanup(self, task_uuid=None):
        """Cleans all platform in env.

        :param task_uuid: Cleans up only resources of specific task.
        :returns: Dict with status of all cleanups
        """
        db.env_set_status(self.uuid, STATUS.READY, STATUS.CLEANING)

        result = {}
        for p in self._get_platforms():
            try:
                cleanup_info = p.cleanup(task_uuid)
                jsonschema.validate(cleanup_info, self._CLEANUP_FORMAT)
            except Exception as e:
                msg = "Plugin %s.cleanup() method is broken" % p.get_fullname()
                LOG.exception(msg)
                cleanup_info = {
                    "discovered": 0, "deleted": 0, "failed": 0,
                    "resources": {}, "errors": [{"message": msg}]
                }
                if not isinstance(e, jsonschema.ValidationError):
                    cleanup_info["errors"][0]["traceback"] = sys.exc_info()

            result[p.get_fullname()] = cleanup_info

        db.env_set_status(self.uuid, STATUS.CLEANING, STATUS.READY)
        return result

    def destroy(self, skip_cleanup=False):
        """Destroys all platforms related to env.

        :param skip_cleanup: By default, before destroying plaform it's cleaned
        """
        cleanup_info = {"skipped": True}
        if not skip_cleanup:
            cleanup_info = self.cleanup()
            cleanup_info["skipped"] = False
            if cleanup_info["errors"]:
                return {
                    "cleanup_info": cleanup_info,
                    "destroy_info": {
                        "skipped": True,
                        "platforms": {},
                        "message": "Skipped because cleanup failed"
                    }
                }

        result = {
            "cleanup_info": cleanup_info,
            "destroy_info": {
                "skipped": False,
                "platforms": {}
            }
        }

        db.env_set_status(self.uuid, STATUS.READY, STATUS.DESTROYING)

        platforms = result["destroy_info"]["platforms"]
        new_env_status = STATUS.DESTROYED

        for p in self._get_platforms():
            name = p.get_fullname()
            platforms[name] = {"status": {"old": p.status}}
            if p.status == platform.STATUS.DESTROYED:
                platforms[name]["status"]["new"] = p.status
                platforms[name]["message"] = (
                    "Platform is already destroyed. Do nothing")
                continue

            db.platform_set_status(
                p.uuid, p.status, platform.STATUS.DESTROYING)
            try:
                p.destroy()
            except Exception:
                db.platform_set_status(p.uuid,
                                       platform.STATUS.DESTROYING,
                                       platform.STATUS.FAILED_TO_DESTROY)
                platforms[name]["message"] = "Failed to destroy"
                platforms[name]["status"]["new"] = (
                    platform.STATUS.FAILED_TO_DESTROY)
                platforms[name]["traceback"] = sys.exc_info()
                new_env_status = STATUS.FAILED_TO_DESTROY
            else:
                db.platform_set_status(p.uuid,
                                       platform.STATUS.DESTROYING,
                                       platform.STATUS.DESTROYED)
                platforms[name]["message"] = "Successfully destroyed"
                platforms[name]["status"]["new"] = platform.STATUS.DESTROYED

        db.env_set_status(self.uuid, STATUS.DESTROYING, new_env_status)

        return result

    def delete(self, force=False):
        """Cascade delete of DB records related to env.

        It deletes all Task and Verify results related to this env as well.

        :param Force: Use it if you don't want to perform status check
        """
        _status = self.status
        if not force and _status != STATUS.DESTROYED:
            raise exceptions.ManagerInvalidState(
                mgr="Env", expected=STATUS.DESTROYED, actual=_status)
        db.env_delete_cascade(self.uuid)
