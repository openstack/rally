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

    @classmethod
    def validate(cls, config, non_hidden=False):
        if non_hidden and cls.__ctx_hidden__:
            raise exceptions.NoSuchContext(name=cls.__ctx_name__)
        jsonschema.validate(config, cls.CONFIG_SCHEMA)

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

    @staticmethod
    def run(context, func, *args, **kwargs):
        ctxlst = [Context.get_by_name(name) for name in context["config"]]
        ctxlst = map(lambda ctx: ctx(context),
                     sorted(ctxlst, key=lambda x: x.__ctx_order__))

        return ContextManager._magic(ctxlst, func, *args, **kwargs)

    @staticmethod
    def validate(context, non_hidden=False):
        for name, config in context.iteritems():
            Context.get_by_name(name).validate(config, non_hidden=non_hidden)

    @staticmethod
    def _magic(ctxlst, func, *args, **kwargs):
        """Some kind of contextlib.nested but with black jack & recursion.

        This method uses recursion to build nested "with" from list of context
        objects. As it's actually a combination of dark and voodoo magic I
        called it "_magic". Please don't repeat at home.

        :param ctxlst: list of instances of subclasses of Context
        :param func: function that will be called inside this context
        :param args: args that will be passed to function `func`
        :param kwargs: kwargs that will be passed to function `func`
        :returns: result of function call
        """
        if not ctxlst:
            return func(*args, **kwargs)

        with ctxlst[0]:
            # TODO(boris-42): call of setup could be moved inside __enter__
            #                 but it should be in try-except, and in except
            #                 we should call by hand __exit__
            ctxlst[0].setup()
            tmp = ContextManager._magic(ctxlst[1:], func, *args, **kwargs)
            return tmp
