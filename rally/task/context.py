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

from rally.common import logging
from rally.common.plugin import plugin
from rally.common import utils
from rally.task import functional

LOG = logging.getLogger(__name__)


def configure(name, order, namespace="default", hidden=False):
    """Context class wrapper.

    Each context class has to be wrapped by configure() wrapper. It
    sets essential configuration of context classes. Actually this wrapper just
    adds attributes to the class.

    :param name: Name of the class, used in the input task
    :param order: As far as we can use multiple context classes that sometimes
                  depend on each other we have to specify order of execution.
                  Contexts with smaller order are run first
    :param hidden: If it is true you won't be able to specify context via
                   task config
    """
    def wrapper(cls):
        cls = plugin.configure(name=name, namespace=namespace,
                               hidden=hidden)(cls)
        cls._meta_set("order", order)
        return cls

    return wrapper


# TODO(andreykurilin): move it to some common place.
@six.add_metaclass(abc.ABCMeta)
class BaseContext(plugin.Plugin, functional.FunctionalMixin,
                  utils.RandomNameGeneratorMixin):
    """This class is a factory for context classes.

    Every context class should be a subclass of this class and implement
    2 abstract methods: setup() and cleanup()

    It covers:
        1) proper setting up of context config
        2) Auto discovering & get by name
        3) Validation by CONFIG_SCHEMA
        4) Order of context creation

    """
    RESOURCE_NAME_FORMAT = "c_rally_XXXXXXXX_XXXXXXXX"

    CONFIG_SCHEMA = {"type": "null"}

    def __init__(self, ctx):
        config = ctx.get("config", {}).get(self.get_name(), {})
        # NOTE(amaretskiy): self.config is a constant data and must be
        #                   immutable or write-protected type to prevent
        #                   unexpected changes in runtime
        if isinstance(config, dict):
            if hasattr(self, "DEFAULT_CONFIG"):
                for key, value in self.DEFAULT_CONFIG.items():
                    config.setdefault(key, value)
            self.config = utils.LockedDict(config)
        elif isinstance(config, list):
            self.config = tuple(config)
        else:
            # NOTE(amaretskiy): It is improbable that config can be a None,
            #                   number, boolean or even string,
            #                   however we handle this
            self.config = config
        self.context = ctx

    def __lt__(self, other):
        return self.get_order() < other.get_order()

    def __gt__(self, other):
        return self.get_order() > other.get_order()

    def __eq__(self, other):
        return self.get_order() == other.get_order()

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def validate(cls, config):
        jsonschema.validate(config, cls.CONFIG_SCHEMA)

    @classmethod
    def get_order(cls):
        return cls._meta_get("order")

    @abc.abstractmethod
    def setup(self):
        """Prepare environment for test.

        This method is executed only once before load generation.

        self.config contains input arguments of this context
        self.context contains information that will be passed to scenario

        The goal of this method is to perform all operation to prepare
        environment and store information to self.context that is required
        by scenario.
        """

    @abc.abstractmethod
    def cleanup(self):
        """Clean up environment after load generation.

        This method is run once after load generation is done to cleanup
        environment.

        self.config contains input arguments of this context
        self.context contains information that was passed to scenario
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()


@plugin.base()
class Context(BaseContext):
    def __init__(self, ctx):
        super(Context, self).__init__(ctx)
        self.task = self.context.get("task", {})


class ContextManager(object):
    """Create context environment and run method inside it."""

    def __init__(self, context_obj):
        self._visited = []
        self.context_obj = context_obj

    @staticmethod
    def validate(ctx, allow_hidden=False):
        for name, config in ctx.items():
            Context.get(name, allow_hidden=allow_hidden).validate(config)

    def _get_sorted_context_lst(self):
        return sorted([
            Context.get(ctx_name, allow_hidden=True)(self.context_obj)
            for ctx_name in self.context_obj["config"].keys()])

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
