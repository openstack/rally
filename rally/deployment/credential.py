# Copyright 2017: Mirantis Inc.
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

import abc

import jsonschema
import six

from rally.common.plugin import plugin


def configure(namespace):
    def wrapper(cls):
        cls = plugin.configure(name="credential", namespace=namespace)(cls)
        return cls
    return wrapper


def get(namespace):
    return Credential.get(name="credential", namespace=namespace)


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Credential(plugin.Plugin):
    """Base class for credentials."""

    @abc.abstractmethod
    def to_dict(self):
        """Converts creedential object to dict.

        :returns: dict that can be used to recreate credential using
            constructor: Credential(**credential.to_dict())
        """

    @abc.abstractmethod
    def verify_connection(self):
        """Verifies that credential can be used for connection."""

    @abc.abstractmethod
    def list_services(self):
        """Returns available services.

        :returns: dict
        """


def configure_builder(namespace):
    def wrapper(cls):
        cls = plugin.configure(name="credential_builder",
                               namespace=namespace)(cls)
        return cls
    return wrapper


def get_builder(namespace):
    return CredentialBuilder.get(name="credential_builder",
                                 namespace=namespace)


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class CredentialBuilder(plugin.Plugin):
    """Base class for extensions of ExistingCloud deployment."""

    CONFIG_SCHEMA = {"type": "null"}

    def __init__(self, config):
        self.config = config

    @classmethod
    def validate(cls, config):
        jsonschema.validate(config, cls.CONFIG_SCHEMA)

    @abc.abstractmethod
    def build_credentials(self):
        """Builds credentials from provided configuration"""
