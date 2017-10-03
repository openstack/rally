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

import random

from rally.common import validation
from rally import consts
from rally import exceptions
from rally.plugins.openstack import osclients
from rally.task import context


@validation.configure("check_api_versions")
class CheckOpenStackAPIVersionsValidator(validation.Validator):
    """Additional validation for api_versions context"""

    def validate(self, context, config, plugin_cls, plugin_cfg):
        for client in plugin_cfg:
            client_cls = osclients.OSClient.get(client)
            try:
                if ("service_type" in plugin_cfg[client] or
                        "service_name" in plugin_cfg[client]):
                    client_cls.is_service_type_configurable()

                if "version" in plugin_cfg[client]:
                    client_cls.validate_version(plugin_cfg[client]["version"])

            except exceptions.RallyException as e:
                return self.fail(
                    "Invalid settings for '%(client)s': %(error)s" % {
                        "client": client,
                        "error": e.format_message()})


@validation.add("check_api_versions")
@context.configure(name="api_versions", platform="openstack", order=150)
class OpenStackAPIVersions(context.Context):
    """Context for specifying OpenStack clients versions and service types.

    Some OpenStack services support several API versions. To recognize
    the endpoints of each version, separate service types are provided in
    Keystone service catalog.

    Rally has the map of default service names - service types. But since
    service type is an entity, which can be configured manually by admin(
    via keystone api) without relation to service name, such map can be
    insufficient.

    Also, Keystone service catalog does not provide a map types to name
    (this statement is true for keystone < 3.3 ).

    This context was designed for not-default service types and not-default
    API versions usage.

    An example of specifying API version:

    .. code-block:: json

        # In this example we will launch NovaKeypair.create_and_list_keypairs
        # scenario on 2.2 api version.
        {
            "NovaKeypair.create_and_list_keypairs": [
                {
                    "args": {
                        "key_type": "x509"
                    },
                    "runner": {
                        "type": "constant",
                        "times": 10,
                        "concurrency": 2
                    },
                    "context": {
                        "users": {
                            "tenants": 3,
                            "users_per_tenant": 2
                        },
                        "api_versions": {
                            "nova": {
                                "version": 2.2
                            }
                        }
                    }
                }
            ]
        }

    An example of specifying API version along with service type:

    .. code-block:: json

        # In this example we will launch CinderVolumes.create_and_attach_volume
        # scenario on Cinder V2
        {
            "CinderVolumes.create_and_attach_volume": [
                {
                    "args": {
                        "size": 10,
                        "image": {
                            "name": "^cirros.*-disk$"
                        },
                        "flavor": {
                            "name": "m1.tiny"
                        },
                        "create_volume_params": {
                            "availability_zone": "nova"
                        }
                    },
                    "runner": {
                        "type": "constant",
                        "times": 5,
                        "concurrency": 1
                    },
                    "context": {
                        "users": {
                            "tenants": 2,
                            "users_per_tenant": 2
                        },
                        "api_versions": {
                            "cinder": {
                                "version": 2,
                                "service_type": "volumev2"
                            }
                        }
                    }
                }
            ]
        }

    Also, it possible to use service name as an identifier of service endpoint,
    but an admin user is required (Keystone can return map of service
    names - types, but such API is permitted only for admin). An example:

    .. code-block:: json

        # Similar to the previous example, but `service_name` argument is used
        # instead of `service_type`
        {
            "CinderVolumes.create_and_attach_volume": [
                {
                    "args": {
                        "size": 10,
                        "image": {
                            "name": "^cirros.*-disk$"
                        },
                        "flavor": {
                            "name": "m1.tiny"
                        },
                        "create_volume_params": {
                            "availability_zone": "nova"
                        }
                    },
                    "runner": {
                        "type": "constant",
                        "times": 5,
                        "concurrency": 1
                    },
                    "context": {
                        "users": {
                            "tenants": 2,
                            "users_per_tenant": 2
                        },
                        "api_versions": {
                            "cinder": {
                                "version": 2,
                                "service_name": "cinderv2"
                            }
                        }
                    }
                }
            ]
        }

    """
    VERSION_SCHEMA = {
        "anyOf": [
            {"type": "string", "description": "a string-like version."},
            {"type": "number", "description": "a number-like version."}
        ]
    }
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "patternProperties": {
            "^[a-z]+$": {
                "type": "object",
                "oneOf": [
                    {
                        "description": "version only",
                        "properties": {
                            "version": VERSION_SCHEMA,
                        },
                        "required": ["version"],
                        "additionalProperties": False
                    },
                    {
                        "description": "version and service_name",
                        "properties": {
                            "version": VERSION_SCHEMA,
                            "service_name": {"type": "string"}
                        },
                        "required": ["service_name"],
                        "additionalProperties": False
                    },
                    {
                        "description": "version and service_type",
                        "properties": {
                            "version": VERSION_SCHEMA,
                            "service_type": {"type": "string"}
                        },
                        "required": ["service_type"],
                        "additionalProperties": False
                    }
                ],
            }
        },
        "minProperties": 1,
        "additionalProperties": False
    }

    def setup(self):
        # FIXME(andreykurilin): move all checks to validate method.

        # use admin only when `service_name` is presented
        admin_clients = osclients.Clients(
            self.context.get("admin", {}).get("credential"))
        clients = osclients.Clients(random.choice(
            self.context["users"])["credential"])
        services = clients.keystone.service_catalog.get_endpoints()
        services_from_admin = None
        for client_name, conf in self.config.items():
            if "service_type" in conf and conf["service_type"] not in services:
                raise exceptions.ValidationError(
                    "There is no service with '%s' type in your environment."
                    % conf["service_type"])
            elif "service_name" in conf:
                if not self.context.get("admin", {}).get("credential"):
                    raise exceptions.ContextSetupFailure(
                        ctx_name=self.get_name(),
                        msg="Setting 'service_name' is admin only operation.")
                if not services_from_admin:
                    services_from_admin = dict(
                        [(s.name, s.type)
                         for s in admin_clients.keystone().services.list()])
                if conf["service_name"] not in services_from_admin:
                    raise exceptions.ValidationError(
                        "There is no '%s' service in your environment"
                        % conf["service_name"])

                # TODO(boris-42): Use separate key ["openstack"]["versions"]
                self.context["config"]["api_versions@openstack"][client_name][
                    "service_type"] = services_from_admin[conf["service_name"]]

        # NOTE(boris-42): Required to be backward compatible
        self.context["config"]["api_versions"] = (
            self.context["config"]["api_versions@openstack"])

    def cleanup(self):
        # nothing to do here
        pass
