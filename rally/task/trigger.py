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

import abc

import jsonschema
import six

from rally.common.plugin import plugin

configure = plugin.configure


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class Trigger(plugin.Plugin):
    """Factory for trigger classes."""

    @classmethod
    def validate(cls, config):
        trigger_schema = cls.get(config["name"]).CONFIG_SCHEMA
        jsonschema.validate(config["args"], trigger_schema)

    def __init__(self, config):
        self.config = config

    @abc.abstractmethod
    def get_configured_event_type(self):
        """Returns supported event type."""

    @abc.abstractmethod
    def is_runnable(self, value):
        """Returns True if trigger is active on specified event value."""
