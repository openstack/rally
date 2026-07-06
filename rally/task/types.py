# Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

import abc
import copy
import inspect
import operator
import re
import types
import typing as t

from rally import exceptions
from rally.common import cfg
from rally.common import logging
from rally.common.plugin import plugin
from rally.utils import typeutils


if t.TYPE_CHECKING:  # pragma: no cover
    from rally.common.plugin import info
    from rally.task import scenario

    S = t.TypeVar("S", bound=scenario.Scenario)


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class ConvertConfig(t.TypedDict):
    """Pre-processing config passed to :meth:`ResourceType.pre_process`.

    Built from a ``Convert(type_, **extra)`` / ``@types.convert`` mapping: the
    resource ``type`` name plus any extra keys. A resource type that reads the
    extra keys may subclass this and narrow its ``pre_process`` override.
    """

    type: str


def convert(
    **kwargs: dict[str, t.Any]
) -> t.Callable[[type[S]], type[S]]:
    """Decorator to define resource transformation(s) on scenario parameters.

    The ``kwargs`` passed as arguments are used to map a key in the
    scenario config to the resource type plugin used to perform a
    transformation on the value of the key. For instance:

        @types.convert(image={"type": "glance_image"})

    This would convert the ``image`` key in the scenario configuration
    to a Glance image by using the ``glance_image`` resource
    plugin. Currently, ``type`` is the only recognized key, but others
    may be added in the future.
    """

    def wrapper(cls: type[S]) -> type[S]:
        for k, v in kwargs.items():
            if "type" not in v:
                LOG.warning(
                    "The configuration for preprocessing '%s' argument of"
                    " %s Scenario plugin is wrong. Check documentation "
                    "for more details." % (k, cls.get_name()))

        cls._meta_setdefault("preprocessors", {})
        cls._meta_get("preprocessors").update(kwargs)
        return cls
    return wrapper


class Convert:
    """Declare the resource type that pre-processes an annotated argument.

    The annotation form of :func:`convert`, co-located with the argument so
    scenarios stay decoupled from the converter class::

        image: t.Annotated[str, Convert("glance_image")]
        image: t.Annotated[str, Convert("glance_image", list_kwargs={...})]
    """

    def __init__(self, type_: str, /, **config: t.Any) -> None:
        """Declare a converter for the annotated argument.

        :param type_: name of a registered :class:`ResourceType` plugin.
        :param config: extra keyword arguments forwarded to the resource
            type's ``pre_process(config=...)``.
        """
        self.type = type_
        self.config = config

    @property
    def type_cfg(self) -> ConvertConfig:
        """The ``{"type": ..., **extra}`` config consumed by preprocessing."""
        return {
            "type": self.type,
            **self.config  # type: ignore[typeddict-item]
        }


class DeferredResource(abc.ABC):
    """A ``pre_process`` result resolved per iteration.

    Returned instead of a plain value when the final value depends on the
    running scenario (its narrowed per-iteration user/tenant and clients). The
    runner replaces the argument with :meth:`resolve` once the scenario for the
    iteration exists.

    A ``DeferredResource`` MUST be picklable, as it is sent to worker processes
    and deep-copied per iteration, so it must hold only plain data, never a
    live client. :meth:`resolve` must be side-effect-free and cheap (e.g.
    filter a list fetched once at build time).
    """

    @abc.abstractmethod
    def resolve(self, scenario: scenario.Scenario) -> t.Any:
        """Return the per-iteration value, given the running scenario."""


def _find_convert_marker(hint: t.Any) -> tuple[Convert, t.Any] | None:
    """Return the ``Convert`` marker and the annotated base type, or None."""

    if t.get_origin(hint) in (t.Union, types.UnionType):
        to_iterate = t.get_args(hint)
    else:
        to_iterate = [hint]

    for arg in to_iterate:
        if t.get_origin(arg) is t.Annotated:
            ann_args = t.get_args(arg)
            for meta in ann_args[1:]:
                if isinstance(meta, Convert):
                    return meta, ann_args[0]
    return None


def collect_scenario_args_preprocessors(
    scenario_cls: type[scenario.Scenario],
    hints: dict[str, t.Any]
) -> dict[str, ConvertConfig]:
    """Merge the ``@types.convert`` decorator and inline ``Convert`` markers.

    An annotation marker wins over the decorator on conflict.
    """
    converters: dict[str, ConvertConfig] = dict(
        scenario_cls._meta_get("preprocessors", default={}))

    for name, hint in hints.items():
        res = _find_convert_marker(hint)
        if res:
            converters[name] = res[0].type_cfg

    return converters


def preprocess(
    name: str,
    context: dict[str, t.Any],
    args: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Run preprocessor on scenario arguments.

    :param name: Scenario plugin name
    :param context: dict with contexts data
    :param args: Scenario arguments for the workload

    :returns processed_args: dictionary object with additional client
                             and resource configuration

    """
    from rally.task import scenario

    scenario_cls = scenario.Scenario.get(name)
    try:
        hints: dict[str, t.Any] = t.get_type_hints(scenario_cls.run,
                                                   include_extras=True)
    except Exception as e:
        LOG.debug(
            f"Cannot resolve type hints for {scenario_cls.__name__}.run(): {e}"
        )
        hints = {}
    preprocessors = collect_scenario_args_preprocessors(scenario_cls,
                                                        hints=hints)

    processed_args = copy.deepcopy(args)

    cache: dict[str, t.Any] = {}
    resource_types: dict[str, ResourceType] = {}
    legacy_types: set[str] = set()
    for src, type_cfg in preprocessors.items():
        if src not in processed_args:
            # a converter runs only for an argument present in the task
            continue
        rtype = type_cfg["type"]
        if rtype not in resource_types:
            resource_cls = ResourceType.get(rtype)
            try:
                if "output_type" not in inspect.signature(
                        resource_cls.pre_process).parameters:
                    legacy_types.add(rtype)
                    LOG.warning(
                        f"Resource type '{rtype}' uses the deprecated legacy "
                        "pre_process(resource_spec, config) contract; add the "
                        "keyword-only output_type parameter."
                    )

                # Legacy resource type plugin may or may not override parent
                #   `__init__`, so we need to be careful here and recheck
                if "scenario_cls" in inspect.signature(
                        resource_cls.__init__).parameters:
                    resource_types[rtype] = resource_cls(
                        context=context, cache=cache, scenario_cls=scenario_cls
                    )
                else:
                    resource_types[rtype] = (
                        resource_cls(context, cache)  # type: ignore[call-arg]
                    )
            except Exception:
                raise exceptions.RallyException(
                    f"Failed to initialize '{rtype}' resource type."
                )
        preprocessor = resource_types[rtype]

        if rtype in legacy_types:
            res = preprocessor.pre_process(  # type: ignore[call-arg]
                processed_args[src], type_cfg
            )
        else:
            hint = _find_convert_marker(hints.get(src))
            res = preprocessor.pre_process(
                resource_spec=processed_args[src],
                config=type_cfg,
                output_type=hint[1] if hint else None,
            )

        if res is not None:
            processed_args[src] = res
    return processed_args


def _compose_jsonschema(resource_cls: type[ResourceType]) -> dict[str, t.Any]:
    """JSON Schema of the specification a resource type accepts.

    Derived from the ``resource_spec`` annotation of its ``pre_process``;
    unconstrained (``{}``) when it is absent or ``Any``.
    """
    try:
        hints = t.get_type_hints(resource_cls.pre_process, include_extras=True)
    except Exception as e:
        msg = (f"Resource type '{resource_cls.get_name()}' has an "
               f"unresolvable pre_process() type annotation: {e}")
        if CONF.strict_type_annotations:
            raise exceptions.InvalidScenarioArgument(msg)
        LOG.warning(msg)
        return {}
    hint = hints.get("resource_spec")
    if hint is None:
        return {}
    try:
        schema = typeutils.hint_to_schema(hint)
    except typeutils.UnsupportedType:
        return {}
    return schema if schema is not None else {}


@plugin.base()
class ResourceType(plugin.Plugin, metaclass=abc.ABCMeta):
    """Base class for a resource type, a named argument pre-processor.

    A resource type resolves a scenario argument from the short specification a
    user writes in a task into the concrete value ``run()`` receives. A
    scenario binds an argument to a resource type by name: inline with
    ``types.Convert("<name>")`` in the argument annotation, or via the
    ``@types.convert`` decorator. ``pre_process()`` is then called once per
    workload for each bound argument, before the scenario runs.

    For example, the built-in ``file`` resource type receives a path and
    returns the file's contents; an OpenStack ``glance_image`` type receives an
    image name, regex or spec dict and returns a concrete image id.
    """

    def __init__(
        self,
        *,
        context: dict[str, t.Any],
        cache: dict[str, t.Any] | None = None,
        scenario_cls: type[scenario.Scenario],
    ) -> None:
        self._context = context
        self._scenario_cls = scenario_cls
        self._global_cache = cache if cache is not None else {}
        self._global_cache.setdefault(self.get_name(), {})
        self._cache = self._global_cache[self.get_name()]

    @classmethod
    def get_info(cls) -> info._PluginInfo:  # type: ignore[misc]
        info_ = super().get_info()
        info_["schema"] = _compose_jsonschema(cls)
        return info_

    @abc.abstractmethod
    def pre_process(
        self,
        *,
        resource_spec: t.Any,
        config: ConvertConfig,
        output_type: t.Any,
    ) -> t.Any:
        """Resolve one argument's specification into its final value.

        This modern signature receives ``output_type`` and may return a
        :class:`DeferredResource` to finish resolving per iteration. The
        deprecated legacy form implements only the two leading positional
        parameters ``(resource_spec, config)`` and is detected automatically
        (a warning is logged). Either form is called only for an argument
        present in the task.

        :param resource_spec: the value written for this argument in the task
            (the pre-conversion specification); its type annotation is the
            schema the task input is validated against
        :param config: the ``Convert`` / ``@types.convert`` config for this
            argument, ``{"type": "<name>", ...}`` (see :class:`ConvertConfig`)
        :param output_type: the argument's annotation base type, so the return
            shape can follow the declared type (an id vs the whole object)
        :returns: the value ``run()`` receives, ``None`` to leave the argument
            untouched, or a :class:`DeferredResource` for per-iteration resolve
        """


def obj_from_name(
    resource_config: dict[str, t.Any],
    resources: t.Iterable[t.Any],
    typename: str
) -> t.Any:
    """Return the resource whose name matches the pattern.

    resource_config has to contain `name`, as it is used to lookup a resource.
    Value of the name will be treated as regexp.

    An `InvalidScenarioArgument` is thrown if the pattern does
    not match unambiguously.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource object uniquely mapped to `name` or `regex`
    """
    if "name" in resource_config:
        # In a case of pattern string exactly matches resource name
        matching_exact = [resource for resource in resources
                          if resource.name == resource_config["name"]]
        if len(matching_exact) == 1:
            return matching_exact[0]
        elif len(matching_exact) > 1:
            raise exceptions.InvalidScenarioArgument(
                "{typename} with name '{pattern}' "
                "is ambiguous, possible matches "
                "by id: {ids}".format(typename=typename.title(),
                                      pattern=resource_config["name"],
                                      ids=", ".join(map(
                                                    operator.attrgetter("id"),
                                                    matching_exact))))
        # Else look up as regex
        patternstr = resource_config["name"]
    elif "regex" in resource_config:
        patternstr = resource_config["regex"]
    else:
        raise exceptions.InvalidScenarioArgument(
            "{typename} 'id', 'name', or 'regex' not found "
            "in '{resource_config}' ".format(typename=typename.title(),
                                             resource_config=resource_config))

    pattern = re.compile(patternstr)
    matching = [resource for resource in resources
                if re.search(pattern, resource.name or "")]
    if not matching:
        raise exceptions.InvalidScenarioArgument(
            "{typename} with pattern '{pattern}' not found".format(
                typename=typename.title(), pattern=pattern.pattern))
    elif len(matching) > 1:
        raise exceptions.InvalidScenarioArgument(
            "{typename} with name '{pattern}' is ambiguous, possible matches "
            "by id: {ids}".format(typename=typename.title(),
                                  pattern=pattern.pattern,
                                  ids=", ".join(map(operator.attrgetter("id"),
                                                    matching))))
    return matching[0]


def obj_from_id(
    resource_config: dict[str, t.Any],
    resources: t.Iterable[t.Any],
    typename: str
) -> t.Any:
    """Return the resource whose name matches the id.

    resource_config has to contain `id`, as it is used to lookup a resource.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource object mapped to `id`
    """
    if "id" in resource_config:
        matching = [resource for resource in resources
                    if resource.id == resource_config["id"]]
        if len(matching) == 1:
            return matching[0]
        else:
            raise exceptions.InvalidScenarioArgument(
                "{typename} with id '{id}' not found".format(
                    typename=typename.title(), id=resource_config["id"]))
    else:
        raise exceptions.InvalidScenarioArgument(
            "{typename} 'id' not found in '{resource_config}'".format(
                typename=typename.title(), resource_config=resource_config))


def _id_from_name(
    resource_config: dict[str, t.Any],
    resources: t.Iterable[t.Any],
    typename: str,
    id_attr: str = "id"
) -> t.Any:
    """Return the id of the resource whose name matches the pattern.

    resource_config has to contain `name`, as it is used to lookup an id.
    Value of the name will be treated as regexp.

    An `InvalidScenarioArgument` is thrown if the pattern does
    not match unambiguously.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource
    :param id_attr: id or uuid should be returned

    :returns: resource id uniquely mapped to `name` or `regex`
    """
    try:
        return getattr(obj_from_name(resource_config, resources, typename),
                       id_attr)
    except AttributeError:
        raise exceptions.RallyException(
            "There is no attribute {attr} in the object {type}".format(
                attr=id_attr, type=typename))


def _name_from_id(
    resource_config: dict[str, t.Any],
    resources: t.Iterable[t.Any],
    typename: str
) -> str:
    """Return the name of the resource which has the id.

    resource_config has to contain `id`, as it is used to lookup a name.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource name mapped to `id`
    """
    return obj_from_id(resource_config, resources, typename).name
