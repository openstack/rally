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

import abc
import copy
import operator
import re

import six

from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions
from rally.task import scenario


LOG = logging.getLogger(__name__)


def convert(**kwargs):
    """Decorator to define resource transformation(s) on scenario parameters.

    The ``kwargs`` passed as arguments are used to map a key in the
    scenario config to the resource type plugin used to perform a
    transformation on the value of the key. For instance:

        @types.convert(image={"type": "glance_image"})

    This would convert the ``image`` key in the scenario configuration
    to a Glance image by using the ``glance_image`` resource
    plugin. Currently ``type`` is the only recognized key, but others
    may be added in the future.
    """

    def wrapper(cls):
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


def preprocess(name, context, args):
    """Run preprocessor on scenario arguments.

    :param name: Scenario plugin name
    :param context: dict with contexts data
    :param args: Scenario arguments for the workload

    :returns processed_args: dictionary object with additional client
                             and resource configuration

    """
    preprocessors = scenario.Scenario.get(name)._meta_get(
        "preprocessors", default={})

    processed_args = copy.deepcopy(args)

    cache = {}
    resource_types = {}
    for src, type_cfg in preprocessors.items():
        if type_cfg["type"] not in resource_types:
            resource_cls = ResourceType.get(type_cfg["type"])
            resource_types[type_cfg["type"]] = resource_cls(context, cache)

        preprocessor = resource_types[type_cfg["type"]]
        if src in processed_args:
            res = preprocessor.pre_process(
                resource_spec=processed_args[src], config=type_cfg)
            if res is not None:
                processed_args[src] = res
    return processed_args


@plugin.base()
@six.add_metaclass(abc.ABCMeta)
class ResourceType(plugin.Plugin):

    def __init__(self, context, cache=None):
        self._context = context
        self._global_cache = cache if cache is not None else {}
        self._global_cache.setdefault(self.get_name(), {})
        self._cache = self._global_cache[self.get_name()]

    @abc.abstractmethod
    def pre_process(self, resource_spec, config):
        """Pre-process resource.

        :param resource_spec: A specification of the resource from the task
        :param config: A configuration for preprocessing taken from the plugin
        """


def obj_from_name(resource_config, resources, typename):
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


def obj_from_id(resource_config, resources, typename):
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


def _id_from_name(resource_config, resources, typename, id_attr="id"):
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


def _name_from_id(resource_config, resources, typename):
    """Return the name of the resource which has the id.

    resource_config has to contain `id`, as it is used to lookup a name.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource name mapped to `id`
    """
    return obj_from_id(resource_config, resources, typename).name
