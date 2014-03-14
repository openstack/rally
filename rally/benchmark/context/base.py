# Copyright 2014: Mirantis Inc.
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

from rally import exceptions
from rally import utils


@six.add_metaclass(abc.ABCMeta)
class Context(object):
    """We will use this class in future as a factory for context classes.

        It will cover:
            1) Auto discovering
            2) Validation of input args
            3) Common logging

        Actually the same functionionallity as
        runners.base.ScenarioRunner and scenarios.base.Scenario
    """

    __name__ = "basecontext"

    CONFIG_SCHEMA = {}

    def __init__(self, context):
        self.config = context.get("config", {}).get(self.__name__, {})
        self.context = context
        self.task = context["task"]

    @staticmethod
    def validate(cls, context):
        jsonschema.validate(context, cls.CONFIG_SCHEMA)

    @staticmethod
    def get_by_name(name):
        """Returns Context class by name."""
        for context in utils.itersubclasses(Context):
            if name == context.__name__:
                return context
        raise exceptions.NoSuchContext(name=name)

    @abc.abstractmethod
    def setup(self):
        """This method sets context of benchmark."""

    @abc.abstractmethod
    def cleanup(self):
        """This method cleans context of benchmark."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()
