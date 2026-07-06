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

from __future__ import annotations

import copy
import inspect
import random
import typing as t

from rally import exceptions
from rally.common import cfg
from rally.common import logging
from rally.common import utils
from rally.common import validation
from rally.common.plugin import plugin
from rally.task import atomic
from rally.task import functional
from rally.task import types
from rally.task.processing import charts
from rally.utils import typeutils


if t.TYPE_CHECKING:  # pragma: no cover
    from rally.common.plugin import info

    S = t.TypeVar("S", bound="Scenario")


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF_OPTS = [
    cfg.StrOpt(
        "scenario_resource_name_format",
        help="A mktemp(1)-like format string that will be used to pattern "
             "the generated random string. It must contain two separate "
             "segments of at least three 'X's; the first one will be replaced "
             "by a portion of the owner ID (i.e task/subtask ID), and the "
             "second will be replaced with a random string."),
    cfg.BoolOpt(
        "strict_type_annotations",
        default=False,
        help="Control how a scenario run() argument annotated with a type "
             "that Rally cannot map to a JSON Schema is handled. When False "
             "(default), such an argument is treated as unconstrained (any "
             "value is accepted) and a warning is logged. When True, building "
             "the scenario's argument schema raises an error instead."),
]
CONF.register_opts(CONF_OPTS)

# re-exported so scenario plugins can write ``scenario.Field(...)`` next to
# ``scenario.configure`` in run() annotations
Field = typeutils.Field


def configure(
    name: str,
    platform: str = "default",
    context: dict[str, t.Any] | None = None
) -> t.Callable[[type[S]], type[S]]:
    """Configure scenario by setting proper meta data.

    This can also transform plain function into scenario plugin, however
    this approach is deprecated - now scenarios must be represented by classes
    based on rally.task.scenario.Scenario.

    :param name: str scenario name
    :param platform: str plugin's platform
    :param context: default task context that is created for this scenario.
                    If there are custom user specified contexts this one
                    will be updated by provided contexts.
    """
    context_dict: dict[str, t.Any] = context or {}

    def wrapper(cls: type[S]) -> type[S]:
        # TODO(boris-42): Drop this check as soon as we refactor rally report
        if "." not in name.strip("."):
            raise exceptions.RallyException(
                "Scenario name must include a dot: '%s'" % name)

        for c in context_dict:
            if "@" not in c:
                msg = ("Old fashion plugin configuration detected in "
                       " `%(scenario)s' scenario. Use full name for "
                       " `%(context)s' context like %(context)s@platform "
                       "where 'platform' is a name of context platform ("
                       "openstack, k8s, etc).")
                LOG.warning(msg % {"scenario": "%s@%s" % (name, platform),
                                   "context": c})

        cls = plugin.configure(name=name, platform=platform)(cls)
        cls._meta_setdefault("default_context", {})

        cls._meta_get("default_context").update(context_dict)
        return cls

    return wrapper


class _Output(t.TypedDict):
    additive: list[dict[str, t.Any]]
    complete: list[dict[str, t.Any]]


@validation.add_default("args-spec")
@plugin.base()
class Scenario(plugin.Plugin,
               atomic.ActionTimerMixin,
               functional.FunctionalMixin,
               utils.RandomNameGeneratorMixin,
               validation.ValidatablePluginMixin):
    """This is base class for any scenario.

        All Scenario Plugins should be subclass of this class.
    """
    RESOURCE_NAME_FORMAT = "s_rally_XXXXXXXX_XXXXXXXX"

    @classmethod
    def _get_resource_name_format(cls) -> str:
        return (CONF.scenario_resource_name_format
                or super(Scenario, cls)._get_resource_name_format())

    def __init__(self, context: dict[str, t.Any] | None = None) -> None:
        super(Scenario, self).__init__()
        self.context = context or {}
        self.task = self.context.get("task", {})
        self._idle_duration = 0.0
        self._output: _Output = dict(additive=[], complete=[])

    def get_owner_id(self) -> str | None:
        if "owner_id" in self.context:
            return self.context["owner_id"]
        return super(Scenario, self).get_owner_id()

    @classmethod
    def get_default_context(cls) -> dict[str, t.Any]:
        return copy.deepcopy(cls._meta_get("default_context"))

    def sleep_between(
        self,
        min_sleep: float,
        max_sleep: float | None = None,
        atomic_delay: float = 0.1
    ) -> None:
        """Call an interruptable_sleep() for a random amount of seconds.

        The exact time is chosen uniformly randomly from the interval
        [min_sleep; max_sleep). The method also updates the idle_duration
        variable to take into account the overall time spent on sleeping.

        :param min_sleep: Minimum sleep time in seconds (non-negative)
        :param max_sleep: Maximum sleep time in seconds (non-negative)
        :param atomic_delay: parameter with which  time.sleep would be called
                             int(sleep_time / atomic_delay) times.
        """
        if max_sleep is None:
            max_sleep = min_sleep

        if not 0 <= min_sleep <= max_sleep:
            raise exceptions.InvalidArgumentsException(
                "0 <= min_sleep <= max_sleep")

        sleep_time = random.uniform(min_sleep, max_sleep)
        utils.interruptable_sleep(sleep_time, atomic_delay)
        self._idle_duration += sleep_time

    def idle_duration(self) -> float:
        """Returns duration of all sleep_between."""
        return self._idle_duration

    def add_output(
        self,
        additive: dict[str, t.Any] | None = None,
        complete: dict[str, t.Any] | None = None
    ) -> None:
        """Add iteration's custom output data.

        This saves custom output data to task results. The main way to get
        this data processed is to find it in HTML report ("Scenario Data"
        tab), where it is displayed by tables or various charts (StackedArea,
        Lines, Pie).

        Take a look at "Processing Output Charts" section of Rally Plugins
        Reference to find explanations and examples about additive and
        complete output types and how to display this output data by
        specific widgets.

        Here is a simple example how to add both additive and complete data
        and display them by StackedArea widget in HTML report:

        .. code-block:: python

            self.add_output(
                additive={"title": "Additive data in StackedArea",
                          "description": "Iterations trend for foo and bar",
                          "chart_plugin": "StackedArea",
                          "data": [["foo", 12], ["bar", 34]]},
                complete={"title": "Complete data as stacked area",
                          "description": "Data is shown as-is in StackedArea",
                          "chart_plugin": "StackedArea",
                          "data": [["foo", [[0, 5], [1, 42], [2, 15]]],
                                   ["bar", [[0, 2], [1, 1.3], [2, 5]]]],
                          "label": "Y-axis label text",
                          "axis_label": "X-axis label text"})

        :param additive: dict with additive output
        :param complete: dict with complete output
        :raises RallyException: if output has wrong format
        """
        for key, value in (("additive", additive), ("complete", complete)):
            if value:
                message = charts.validate_output(key, value)
                if message:
                    raise exceptions.RallyException(message)
                self._output[
                    key  # type: ignore[literal-required]
                ].append(value)

    if not t.TYPE_CHECKING:
        def run(self, **kwargs: t.Any) -> None:
            """Execute the scenario's workload.

            This method must be implemented by all scenario plugins.
            It defines the actual workload that the scenario will execute.

            :param kwargs: Scenario-specific arguments from task configuration
            """
            raise NotImplementedError()
    else:
        run: t.Callable

    @classmethod
    def _get_doc(cls) -> str:
        """Get scenario documentation from run method."""
        return cls.run.__doc__ or ""

    @classmethod
    def _arg_property_schemas(cls) -> tuple[dict[str, t.Any], bool]:
        """Return the per-argument schemas and whether extra args are allowed.

        The schemas come from the ``run()`` type annotations, plus the input
        schema of any converted argument. A converter describes the value the
        user writes before conversion, which overrides the post-conversion type
        from the annotation. The flag is True when ``run()`` accepts
        ``**kwargs``.
        """
        properties: dict[str, t.Any] = {}
        additional = False

        try:
            hints = t.get_type_hints(cls.run, include_extras=True)
        except Exception as e:
            msg = f"Cannot resolve type hints for {cls.__name__}.run(): {e}"
            if CONF.strict_type_annotations:
                raise exceptions.InvalidScenarioArgument(msg)
            LOG.warning(msg)
            return properties, additional

        for name, param in inspect.signature(cls.run).parameters.items():
            if name in ("self", "cls"):
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                additional = True  # **kwargs -> extra args allowed
                continue
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            if name in hints:
                try:
                    schema = typeutils.hint_to_schema(hints[name])
                except typeutils.UnsupportedType:
                    if CONF.strict_type_annotations:
                        raise exceptions.InvalidScenarioArgument(
                            f"'{name}' has an unsupported type annotation: "
                            f"{hints[name]!r}"
                        )
                    LOG.warning(
                        f"Scenario argument '{name}' has an unsupported "
                        f"type annotation {hints[name]!r}; "
                        f"it is not validated (treated as 'Any'). "
                        f"Set [DEFAULT]strict_type_annotations=True "
                        f"to fail instead."
                    )
                    schema = None

                if schema is not None:
                    properties[name] = schema

        preprocessors = types.collect_scenario_args_preprocessors(cls, hints)
        for arg, type_cfg in preprocessors.items():
            type_name = type_cfg.get("type")
            if not type_name:
                continue
            try:
                resource_cls = types.ResourceType.get(type_name)
            except exceptions.PluginNotFound:
                continue

            properties[arg] = types._compose_jsonschema(resource_cls)

        return properties, additional

    @classmethod
    def get_title(cls) -> str:
        # `rally plugin list` only needs the title, so skip the
        # argument-schema build that get_info would otherwise do.
        return super(Scenario, cls).get_info()["title"]

    @classmethod
    def get_info(cls) -> info._PluginInfo:
        """Expose the scenario ``args`` as ``info["schema"]``.

        The schema is an object covering both the typed/converter arguments and
        the documented parameters: the annotation or converter schema where we
        have one, plus the docstring ``:param`` text as a ``description``. Both
        argument validation and the docs/``plugin show`` renderers read from
        this single place (``parameters`` is still populated for backward
        compatibility).

        A ``:param`` that names no real ``run()`` argument (with no
        ``**kwargs`` to absorb it) is a docstring/signature mismatch. It is
        still surfaced in the schema so the docs keep it, but a warning is
        logged (or an error, under strict-type-annotations mode).
        """
        plugin_info = super(Scenario, cls).get_info()
        arg_props, additional = cls._arg_property_schemas()
        docs = {p["name"]: p["doc"] for p in plugin_info["parameters"]}
        if arg_props or docs:
            if not additional:
                # no **kwargs -> every documented name must be a real argument
                real = {n for n in inspect.signature(cls.run).parameters
                        if n not in ("self", "cls")}
                for name in docs:
                    if name not in real and name not in arg_props:
                        msg = (
                            f"Scenario '{cls.get_name()}': ':param {name}:' "
                            f"documents an argument that run() does not accept"
                        )
                        if CONF.strict_type_annotations:
                            raise exceptions.InvalidScenarioArgument(msg)
                        LOG.warning(
                            f"{msg}; it is shown in the docs but not "
                            f"validated. "
                            f"Set [DEFAULT]strict_type_annotations=True "
                            f"to fail instead."
                        )
            # documented params first (in order), then any typed args that are
            # not documented, so an annotated arg never escapes the schema.
            names = list(docs) + [n for n in arg_props if n not in docs]
            properties: dict[str, t.Any] = {}
            for name in names:
                prop = dict(arg_props.get(name, {}))
                if docs.get(name):
                    prop["description"] = docs[name]
                properties[name] = prop
            plugin_info["schema"] = {"type": "object",
                                     "additionalProperties": additional,
                                     "properties": properties}
        return plugin_info
