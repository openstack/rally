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
from rally import log as logging
from rally import utils

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Context(object):
    """This class is a factory for context classes.

    Every context class should be a subclass of this class and implement
    2 abstract methods: setup() and cleanup()

    It covers:
        1) proper setting up of context config
        2) Auto discovering & get by name
        3) Validation by CONFIG_SCHEMA
        4) Order of context creation

    """
    __ctx_name__ = "base"
    __ctx_order__ = 0
    __ctx_hidden__ = True

    CONFIG_SCHEMA = {}

    def __init__(self, context):
        self.config = context.get("config", {}).get(self.__ctx_name__, {})
        self.context = context
        self.task = context["task"]

    def __lt__(self, other):
        return self.get_order() < other.get_order()

    def __gt__(self, other):
        return self.get_order() > other.get_order()

    def __eq__(self, other):
        return self.get_order() == other.get_order()

    @classmethod
    def validate(cls, config, non_hidden=False):
        if non_hidden and cls.__ctx_hidden__:
            raise exceptions.NoSuchContext(name=cls.__ctx_name__)
        jsonschema.validate(config, cls.CONFIG_SCHEMA)

    @classmethod
    def validate_semantic(cls, config, admin=None, users=None, task=None):
        """Context semantic validation towards the deployment."""

    @classmethod
    def get_name(cls):
        return cls.__ctx_name__

    @classmethod
    def get_order(cls):
        return cls.__ctx_order__

    @staticmethod
    def get_by_name(name):
        """Return Context class by name."""
        for context in utils.itersubclasses(Context):
            if name == context.__ctx_name__:
                return context
        raise exceptions.NoSuchContext(name=name)

    @abc.abstractmethod
    def setup(self):
        """Set context of benchmark."""

    @abc.abstractmethod
    def cleanup(self):
        """Clean context of benchmark."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()


class ContextManager(object):
    """Create context environment and run method inside it."""

    def __init__(self, context_obj):
        self._visited = []
        self.context_obj = context_obj

    @staticmethod
    def validate(context, non_hidden=False):
        for name, config in context.iteritems():
            Context.get_by_name(name).validate(config, non_hidden=non_hidden)

    @staticmethod
    def validate_semantic(context, admin=None, users=None, task=None):
        for name, config in context.iteritems():
            Context.get_by_name(name).validate_semantic(config, admin=admin,
                                                        users=users, task=task)

    def _get_sorted_context_lst(self):
        ctxlst = map(Context.get_by_name, self.context_obj["config"])
        return sorted(map(lambda ctx: ctx(self.context_obj), ctxlst))

    def setup(self):
        """Creates benchmark environment from config."""

        self._visited = []
        for ctx in self._get_sorted_context_lst():
            self._visited.append(ctx)
            ctx.setup()

        return self.context_obj

    def cleanup(self):
        """Destroys benchmark environment."""

        ctxlst = self._visited or self._get_sorted_context_lst()
        for ctx in ctxlst[::-1]:
            try:
                ctx.cleanup()
            except Exception as e:
                LOG.error("Context %s failed during cleanup." % ctx.get_name())
                LOG.exception(e)

    def __enter__(self):
        try:
            self.setup()
        except Exception:
            self.cleanup()
            raise

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()
