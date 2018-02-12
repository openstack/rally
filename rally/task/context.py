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
import collections

import six

from rally.common import cfg
from rally.common import logging
from rally.common.plugin import plugin
from rally.common import utils
from rally.common import validation
from rally.task import atomic
from rally.task import functional
from rally.task import utils as task_utils


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF_OPTS = [
    cfg.StrOpt(
        "context_resource_name_format",
        help="Template is used to generate random names of resources. X is"
             "replaced with random latter, amount of X can be adjusted")
]
CONF.register_opts(CONF_OPTS)


@logging.log_deprecated_args("Use 'platform' arg instead", "0.10.0",
                             ["namespace"], log_function=LOG.warning)
def configure(name, order, platform="default", namespace=None, hidden=False):
    """Context class wrapper.

    Each context class has to be wrapped by configure() wrapper. It
    sets essential configuration of context classes. Actually this wrapper just
    adds attributes to the class.

    :param name: Name of the class, used in the input task
    :param platform: str plugin's platform
    :param order: As far as we can use multiple context classes that sometimes
                  depend on each other we have to specify order of execution.
                  Contexts with smaller order are run first
    :param hidden: If it is true you won't be able to specify context via
                   task config
    """
    if namespace:
        platform = namespace

    def wrapper(cls):
        cls = plugin.configure(name=name, platform=platform,
                               hidden=hidden)(cls)
        cls._meta_set("order", order)
        return cls

    return wrapper


def add_default_context(name, config):
    """Add default context that is inherit by all children plugins.

    :param name: str, name of the validator plugin
    :param kwargs: dict, arguments used to initialize validator class
        instance
    """

    def wrapper(plugin):
        plugin._default_meta_setdefault("default_context", {})
        plugin._default_meta_get("default_context")[name] = config
        return plugin

    return wrapper


# TODO(andreykurilin): BaseContext is used by Task and Verification and should
#                      be moved to common place
@six.add_metaclass(abc.ABCMeta)
class BaseContext(plugin.Plugin, functional.FunctionalMixin,
                  utils.RandomNameGeneratorMixin, atomic.ActionTimerMixin):
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
        super(BaseContext, self).__init__()
        config = ctx.get("config", {})
        if self.get_name() in config:
            # TODO(boris-42): Fix tests, code is always using fullnames
            config = config[self.get_name()]
        else:
            # TODO(boris-42): use [] instead of get() context full name is
            #                 always presented.
            config = config.get(self.get_fullname(), {})
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
        self.env = self.context.get("env", {})

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


@validation.add_default("jsonschema")
@plugin.base()
class Context(BaseContext, validation.ValidatablePluginMixin):
    def __init__(self, ctx):
        super(Context, self).__init__(ctx)
        self.task = self.context.get("task", {})

    @classmethod
    def _get_resource_name_format(cls):
        return (CONF.context_resource_name_format
                or super(Context, cls)._get_resource_name_format())

    def get_owner_id(self):
        if "owner_id" in self.context:
            return self.context["owner_id"]
        return super(Context, self).get_owner_id()


class ContextManager(object):
    """Create context environment and run method inside it."""

    def __init__(self, context_obj):
        self._visited = []
        self.context_obj = context_obj
        self._data = collections.OrderedDict()

    def contexts_results(self):
        """Returns a list with contexts execution results."""
        return list(self._data.values())

    def _get_sorted_context_lst(self):
        ctx_lst = [Context.get(name, allow_hidden=True)
                   for name in self.context_obj["config"]]
        ctx_lst.sort(key=lambda x: x.get_order())
        return [c(self.context_obj) for c in ctx_lst]

    def _log_prefix(self):
        return "Task %s |" % self.context_obj["task"]["uuid"]

    def setup(self):
        """Creates environment by executing provided context plugins."""
        self._visited = []
        for ctx in self._get_sorted_context_lst():
            ctx_data = {
                "plugin_name": ctx.get_fullname(),
                "plugin_cfg": ctx.config,
                "setup": {
                    "started_at": None,
                    "finished_at": None,
                    "atomic_actions": None,
                    "error": None
                },
                "cleanup": {
                    "started_at": None,
                    "finished_at": None,
                    "atomic_actions": None,
                    "error": None
                }
            }
            self._data[ctx.get_fullname()] = ctx_data
            self._visited.append(ctx)
            msg = ("%(log_prefix)s Context %(name)s setup() "
                   % {"log_prefix": self._log_prefix(),
                      "name": ctx.get_fullname()})

            timer = utils.Timer()
            try:
                with timer:
                    ctx.setup()
            except Exception as exc:
                ctx_data["setup"]["error"] = task_utils.format_exc(exc)
                raise
            finally:
                ctx_data["setup"]["atomic_actions"] = ctx.atomic_actions()
                ctx_data["setup"]["started_at"] = timer.timestamp()
                ctx_data["setup"]["finished_at"] = timer.finish_timestamp()

            LOG.info("%(msg)s finished in %(duration)s"
                     % {"msg": msg, "duration": timer.duration(fmt=True)})

        return self.context_obj

    def cleanup(self):
        """Cleans up  environment by executing provided context plugins."""
        ctxlst = self._visited or self._get_sorted_context_lst()
        for ctx in ctxlst[::-1]:
            ctx.reset_atomic_actions()
            msg = ("%(log_prefix)s Context %(name)s cleanup()"
                   % {"log_prefix": self._log_prefix(),
                      "name": ctx.get_fullname()})
            # NOTE(andreykurilin): As for our code, ctx_data is
            #   always presented. The further checks for `ctx_data is None` are
            #   added just for "disaster cleanup". It is not officially
            #   presented feature and not we provide out-of-the-box, but some
            #   folks have own scripts which are based on ContextManager and
            #   it would be nice to not break them.
            ctx_data = None
            if ctx.get_fullname() in self._data:
                ctx_data = self._data[ctx.get_fullname()]

            timer = utils.Timer()
            try:
                with timer:
                    LOG.info("%s started" % msg)
                    ctx.cleanup()
                LOG.info("%(msg)s finished in %(duration)s"
                         % {"msg": msg, "duration": timer.duration(fmt=True)})
            except Exception as exc:
                LOG.exception(
                    "%(msg)s failed after %(duration)s"
                    % {"msg": msg, "duration": timer.duration(fmt=True)})
                if ctx_data is not None:
                    ctx_data["cleanup"]["error"] = task_utils.format_exc(exc)
            finally:
                if ctx_data is not None:
                    aa = ctx.atomic_actions()
                    ctx_data["cleanup"]["atomic_actions"] = aa
                    ctx_data["cleanup"]["started_at"] = timer.timestamp()
                    finished_at = timer.finish_timestamp()
                    ctx_data["cleanup"]["finished_at"] = finished_at

    def __enter__(self):
        try:
            self.setup()
        except Exception:
            self.cleanup()
            raise

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.cleanup()
