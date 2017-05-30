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

import copy

from rally.common import logging
from rally import consts
from rally.deployment import credential
from rally.deployment import engine

LOG = logging.getLogger(__name__)


@engine.configure(name="ExistingCloud")
class ExistingCloud(engine.Engine):
    """Platform independent deployment engine.

    This deployment engine allows specifing list of credentials for one
    or more platforms.

    Example configuration:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "creds": {
                "openstack": {
                    "auth_url": "http://localhost:5000/v3/",
                    "region_name": "RegionOne",
                    "endpoint_type": "public",
                    "admin": {
                        "username": "admin",
                        "password": "admin",
                        "user_domain_name": "admin",
                        "project_name": "admin",
                        "project_domain_name": "admin",
                    },
                    "https_insecure": False,
                    "https_cacert": "",
                }
            }
        }

    To specify extra options use can use special "extra" parameter:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            ...
            "extra": {"some_var": "some_value"}
        }

    It also support deprecated version of configuration that supports
    only OpenStack.

    keystone v2:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "auth_url": "http://localhost:5000/v2.0/",
            "region_name": "RegionOne",
            "endpoint_type": "public",
            "admin": {
                "username": "admin",
                "password": "password",
                "tenant_name": "demo"
            },
            "https_insecure": False,
            "https_cacert": "",
        }

    keystone v3 API endpoint:

    .. code-block:: json

        {
            "type": "ExistingCloud",
            "auth_url": "http://localhost:5000/v3/",
            "region_name": "RegionOne",
            "endpoint_type": "public",
            "admin": {
                "username": "admin",
                "password": "admin",
                "user_domain_name": "admin",
                "project_name": "admin",
                "project_domain_name": "admin",
            },
            "https_insecure": False,
            "https_cacert": "",
        }

    """

    USER_SCHEMA = {
        "type": "object",
        "oneOf": [
            {
                "description": "Keystone V2.0",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "tenant_name": {"type": "string"},
                },
                "required": ["username", "password", "tenant_name"],
                "additionalProperties": False
            },
            {
                "description": "Keystone V3.0",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "domain_name": {"type": "string"},
                    "user_domain_name": {"type": "string"},
                    "project_name": {"type": "string"},
                    "project_domain_name": {"type": "string"},
                },
                "required": ["username", "password", "project_name"],
                "additionalProperties": False
            }
        ],
    }

    OLD_CONFIG_SCHEMA = {
        "type": "object",
        "description": "Deprecated schema (openstack only)",
        "properties": {
            "type": {"type": "string"},
            "auth_url": {"type": "string"},
            "region_name": {"type": "string"},
            # NOTE(andreykurilin): it looks like we do not use endpoint
            # var at all
            "endpoint": {"type": ["string", "null"]},
            "endpoint_type": {"enum": [consts.EndpointType.ADMIN,
                                       consts.EndpointType.INTERNAL,
                                       consts.EndpointType.PUBLIC,
                                       None]},
            "https_insecure": {"type": "boolean"},
            "https_cacert": {"type": "string"},
            "profiler_hmac_key": {"type": ["string", "null"]},
            "admin": USER_SCHEMA,
            "users": {"type": "array", "items": USER_SCHEMA},
            "extra": {"type": "object", "additionalProperties": True}
        },
        "required": ["type", "auth_url", "admin"],
        "additionalProperties": False
    }

    NEW_CONFIG_SCHEMA = {
        "type": "object",
        "description": "New schema for multiplatform deployment",
        "properties": {
            "type": {"enum": ["ExistingCloud"]},
            "creds": {
                "type": "object",
                "patternProperties": {
                    "^[a-z0-9_-]+$": {
                        "oneOf": [
                            {
                                "description": "Single credential",
                                "type": "object"
                            },
                            {
                                "description": "List of credentials",
                                "type": "array",
                                "items": {"type": "object"}
                            },
                        ]
                    }
                }
            },
            "extra": {"type": "object", "additionalProperties": True}
        },
        "required": ["type", "creds"],
        "additionalProperties": False
    }

    CONFIG_SCHEMA = {"type": "object",
                     "oneOf": [OLD_CONFIG_SCHEMA, NEW_CONFIG_SCHEMA]}

    def validate(self, config=None):
        config = config or self.config
        super(ExistingCloud, self).validate(config)

        creds_config = self._get_creds(config)
        for platform, config in creds_config.items():
            builder_cls = credential.get_builder(platform)
            for creds in config:
                builder_cls.validate(creds)

    def _get_creds(self, config):
        # NOTE(astudenov): copy config to prevent compatibility changes
        # from saving to database
        config = copy.deepcopy(config)
        if "creds" not in config:
            # backward compatibility with old schema
            del config["type"]
            creds_config = {"openstack": [config]}
        else:
            creds_config = config["creds"]

        # convert all credentials to list
        for platform, config in creds_config.items():
            if isinstance(config, dict):
                creds_config[platform] = [config]
        return creds_config

    def make_deploy(self):
        platforms = (["openstack"] if "creds" not in self.config
                     else self.config["creds"].keys())
        LOG.info("Save deployment '%(name)s' (uuid=%(uuid)s) with "
                 "'%(platforms)s' platform%(plural)s." %
                 {"name": self.deployment["name"],
                  "uuid": self.deployment["uuid"],
                  "platforms": "', '".join(platforms),
                  "plural": "s" if len(platforms) > 1 else ""})
        self.deployment.set_started()
        credentials = self.deploy()
        self.deployment.set_completed()
        return credentials

    def deploy(self):
        if "creds" not in self.config:
            LOG.warning("Old config schema is deprecated since Rally 0.10.0. "
                        "Please use new config schema for ExistingCloud")
        creds_config = self._get_creds(self.config)
        parsed_credentials = {}
        for platform, config in creds_config.items():
            builder_cls = credential.get_builder(platform)
            credentials = []
            for creds in config:
                builder = builder_cls(creds)
                credentials.append(builder.build_credentials())
            parsed_credentials[platform] = credentials
        return parsed_credentials

    def cleanup(self):
        pass
