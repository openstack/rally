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
import os
import traceback

import jsonschema

from rally.common import db
from rally.common import logging
from rally.common import utils
from rally.env import platform
from rally import exceptions
from rally import plugins


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

SPEC_SCHEMA = {
    "type": "object",
    "patternProperties": {
        "!version": {
            "enum": [1],
            "description": "Env format version"
        },
        "!description": {
            "type": "string",
            "description": "User specific description of deployment"
        },
        "!extras": {
            "type": "object",
            "description": (
                "External information provided by users, can be used for"
                "integration of other tooling outside of rally or just"
                "providing some specific meta information")
        },
        "!config": {
            "type": "object",
            "properties": {
                "*": {
                    "type": "object",
                    "description": (
                        "Keys are option's name, values are option's values"),
                    "properties": {
                        "*": {"type": "object"}
                    }
                },
            },
            "description": "Keys are groups, values are options names"
        },
        "^[^!@]+(@[^!@]+)?$": {
            "type": "object",
            "description": (
                "Key is platform plugin name, values are plugin specs")
        }
    },
    "additionalProperties": False
}


class EnvManager(object):
    """Implements life cycle management of Rally Envs.

    EnvManager is one of key Rally components, It manages and stores
    information about tested platforms.

    Env manager is using platform plugins to: create, delete, cleanup,
    check health, obtain information about about platforms.

    Every Env has:
    - unique name and UUID
    - dates when it was created and updated
    - default config override
    - platform plugins spec which are used to create platform
    - as well as platform & plugin data which are used by other platform
      commands

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

        This method is not meant to be called directly, use one of
        next class methods: get(), create() or list().
        """
        self._env = copy.deepcopy(_data)
        self._env["platforms"] = []
        self.uuid = self._env["uuid"]

    def __str__(self):
        return "Env `%(name)s (%(uuid)s)'" % self._env

    @property
    def status(self):
        """Returns current state of Env that was fetched from DB."""
        return db.env_get_status(self.uuid)

    @property
    def cached_data(self):
        platforms = {}
        for p in self._env["platforms"]:
            p = copy.deepcopy(p)
            for k in ["created_at", "updated_at"]:
                p[k] = p[k].isoformat()
            platforms[p["platform_name"]] = p

        return {
            "uuid": self._env["uuid"],
            "created_at": self._env["created_at"].isoformat(),
            "updated_at": self._env["updated_at"].isoformat(),
            "name": self._env["name"],
            "description": self._env["description"],
            "status": self._env["status"],
            "spec": copy.deepcopy(self._env["spec"]),
            "extras": copy.deepcopy(self._env["extras"]),
            "platforms": platforms
        }

    @property
    def data(self):
        """Returns full information about env including platforms."""
        self._env = db.env_get(self.uuid)
        self._env["platforms"] = db.platforms_list(self.uuid)
        return self.cached_data

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
    def _validate_and_create_env(cls, name, spec):
        """Validated and create env and platforms DB records.

        Do NOT use this method directly. Call create() method instead.

        - Restore full name of plugin. If only platform name is specified
        plugin with name existing@<platform_name> is going to be used
        - Validates spec using standard plugin validation mechanism
        - Creates env and platforms DB records in DB

        :returns: dict that contains env record stored in DB
        """

        try:
            jsonschema.validate(spec, SPEC_SCHEMA)
        except jsonschema.ValidationError as err:
            raise exceptions.ManagerInvalidSpec(
                mgr="Env", spec=spec, errors=[str(err)])

        spec.pop("!version", None)
        config = spec.pop("!config", {})
        extras = spec.pop("!extras", {})
        description = spec.pop("!description", "")

        existing_platforms = {}
        for p_name, p_spec in list(spec.items()):
            if "@" not in p_name:
                spec["existing@%s" % p_name] = p_spec
                spec.pop(p_name)

            platform_name = p_name.split("@")[1] if "@" in p_name else p_name
            if platform_name in existing_platforms:
                raise exceptions.ManagerInvalidSpec(
                    mgr="Env", spec=spec,
                    errors=["Using multiple plugins [%s, %s] with the same "
                            "platform in single Env is not supported: "
                            % (p_name, existing_platforms[platform_name])]
                )
            existing_platforms[platform_name] = p_name

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
                                 config, spec, _platforms))

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
                    LOG.exception(
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
                    LOG.warning("Couldn't store platform %s data to DB."
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
    @plugins.ensure_plugins_are_loaded
    def create(cls, name, spec, description=None, extras=None, config=None):
        """Creates DB record for new env and returns instance of Env class.

        :param name: User specified name of env
        :param description: User specified description
        :param extras: User specified dict with extra options
        :param spec: Specification that contains info about all
                     platform plugins and their arguments.
        :param config: Reserved for the new feature. Not applicable as for now
        :returns: EnvManager instance corresponding to created Env
        """
        # NOTE(boris-42): this allows to avoid validation copy paste. If spec
        #                 is not dict it will fail during validation process
        if isinstance(spec, dict):
            if description is not None:
                spec["!description"] = description
            if extras is not None:
                spec["!extras"] = extras
            if config is not None:
                spec["!config"] = config

        self = cls._validate_and_create_env(name, spec)
        self._create_platforms()
        return self

    _FROM_SYS_ENV_FORMAT = {
        "type": "object",
        "properties": {
            "available": {"type": "boolean"},
            "message": {"type": "string"},
            "traceback": {"type": "string"},
            "spec": {"type": "object",
                     "additionalProperties": True}
        },
        "required": ["available"],
        "additionalProperties": False
    }

    @classmethod
    @plugins.ensure_plugins_are_loaded
    def create_spec_from_sys_environ(cls, description=None, extras=None,
                                     config=None):
        """Compose an environment spec based on system environment.

        Iterates over all available platform-representation plugins which
        checks system environment for credentials.

        :param description: User specified description to include in the spec
        :param extras: User specified dict with extra options to include in
            the spec
        :param config: Reserved for the new feature. Not applicable as for now
        :returns: A dict with an environment specification and detailed
            information about discovery
        """

        details = {}
        for p in platform.Platform.get_all():
            try:
                res = p.create_spec_from_sys_environ(copy.deepcopy(os.environ))
                jsonschema.validate(res, cls._FROM_SYS_ENV_FORMAT)
                res.setdefault("message", "Available")
            except Exception as e:
                msg = ("Plugin %s.create_from_sys_environ() method is broken"
                       % p.get_fullname())
                LOG.exception(msg)
                res = {"message": msg, "available": False}
                if not isinstance(e, jsonschema.ValidationError):
                    res["traceback"] = traceback.format_exc()
            details[p.get_fullname()] = res
        spec = dict((k, v.get("spec", {}))
                    for k, v in details.items() if v["available"])
        if description is not None:
            spec["!description"] = description
        if extras is not None:
            spec["!extras"] = extras
        if config is not None:
            spec["!config"] = config
        return {"spec": spec, "discovery_details": details}

    def rename(self, new_name):
        """Renames env record.

        :param new_name: New Env name.
        """
        if self._env["name"] == new_name:
            return True
        return db.env_rename(self.uuid, self._env["name"], new_name)

    def update(self, description=None, config=None, extras=None):
        """Update description and extras for environment.

        :param description: New description for env
        :param extras: New extras for env
        """
        return db.env_update(
            self.uuid, description=description, config=config, extras=extras)

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
            "traceback": {"type": "string"}
        },
        "required": ["available"],
        "additionalProperties": False
    }

    @plugins.ensure_plugins_are_loaded
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
                    check_result["traceback"] = traceback.format_exc()

            result[p.get_fullname()] = check_result

        return result

    _INFO_FORMAT = {
        "type": "object",
        "properties": {
            "info": {},
            "error": {"type": "string"},
            "traceback": {"type": "string"},
        },
        "required": ["info"],
        "additionalProperties": False
    }

    @plugins.ensure_plugins_are_loaded
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
                    info["traceback"] = traceback.format_exc()

            result[p.get_fullname()] = info

        return result

    _CLEANUP_FORMAT = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
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
                        "traceback": {"type": "string"}
                    },
                    "required": ["message"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["discovered", "deleted", "failed", "resources", "errors"],
        "additionalProperties": False
    }

    @plugins.ensure_plugins_are_loaded
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
                cleanup_info.setdefault("message", "Succeeded")
                jsonschema.validate(cleanup_info, self._CLEANUP_FORMAT)
            except Exception as e:
                msg = "Plugin %s.cleanup() method is broken" % p.get_fullname()
                LOG.exception(msg)
                cleanup_info = {
                    "message": "Failed",
                    "discovered": 0, "deleted": 0, "failed": 0,
                    "resources": {}, "errors": [{"message": msg}]
                }
                if isinstance(e, NotImplementedError):
                    cleanup_info["message"] = "Not implemented"
                    cleanup_info["errors"] = []
                elif not isinstance(e, jsonschema.ValidationError):
                    cleanup_info["errors"][0]["traceback"] = (
                        traceback.format_exc())

            result[p.get_fullname()] = cleanup_info

        db.env_set_status(self.uuid, STATUS.CLEANING, STATUS.READY)
        return result

    @plugins.ensure_plugins_are_loaded
    def destroy(self, skip_cleanup=False):
        """Destroys all platforms related to env.

        :param skip_cleanup: Skip cleaning up platform resources
        """
        cleanup_info = {"skipped": True}
        if not skip_cleanup:
            cleanup_info["info"] = self.cleanup()
            cleanup_info["skipped"] = False
            cleanup_info["failed"] = bool(any(
                v["errors"] for v in cleanup_info["info"].values()))
            if cleanup_info["failed"]:
                return {
                    "cleanup_info": cleanup_info,
                    "destroy_info": {
                        "skipped": True,
                        "platforms": {},
                        "message": "Skipped because cleanup has errors"
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
                platforms[name]["traceback"] = traceback.format_exc()
                new_env_status = STATUS.FAILED_TO_DESTROY
            else:
                db.platform_set_status(p.uuid,
                                       platform.STATUS.DESTROYING,
                                       platform.STATUS.DESTROYED)
                platforms[name]["message"] = "Successfully destroyed"
                platforms[name]["status"]["new"] = platform.STATUS.DESTROYED

        from rally.common import objects

        # TODO(boris-42): This is breaking all kinds of rules of good
        #                 architecture, and we should remove this thing from
        #                 here...
        for verifier in objects.Verifier.list():
            verifier.set_env(self.uuid)
            verifier.manager.uninstall()

        db.env_set_status(self.uuid, STATUS.DESTROYING, new_env_status)

        return result

    def delete(self, force=False):
        """Cascade delete of DB records related to env.

        It deletes all Task and Verify results related to this env as well.

        :param force: Use it if you don't want to perform status check
        """
        _status = self.status
        if not force and _status != STATUS.DESTROYED:
            raise exceptions.ManagerInvalidState(
                mgr="Env", expected=STATUS.DESTROYED, actual=_status)
        db.env_delete_cascade(self.uuid)

    def get_validation_context(self):
        """Return a validation context for a workload."""
        context = {}
        for p in self._get_platforms():
            context.update(p._get_validation_context())
        return context
