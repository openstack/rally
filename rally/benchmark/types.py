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

from rally.benchmark.scenarios import base
from rally import exceptions
from rally import osclients


def set(**kwargs):
    """Decorator to define resource transformation(s) on scenario parameters.

    The `kwargs` passed as arguments to the decorator are used to
    map a key in the scenario config to the subclass of ResourceType
    used to perform a transformation on the value of that key.
    """
    def wrapper(func):
        func.preprocessors = getattr(func, 'preprocessors', {})
        func.preprocessors.update(kwargs)
        return func
    return wrapper


def preprocess(cls, method_name, context, args):
    """Run preprocessor on scenario arguments.

    :param cls: class name of benchmark scenario
    :param method_name: name of benchmark scenario method
    :param context: dictionary object that must have admin and endpoint entries
    :param args: args section of benchmark specification in rally task file

    :returns processed_args: dictionary object with additional client
                             and resource configuration

    """
    preprocessors = base.Scenario.meta(cls, method_name=method_name,
                                       attr_name="preprocessors", default={})
    clients = osclients.Clients(context["admin"]["endpoint"])
    processed_args = copy.deepcopy(args)

    for src, preprocessor in preprocessors.items():
        resource_cfg = processed_args.get(src)
        if resource_cfg:
            processed_args[src] = preprocessor.transform(
                clients=clients, resource_config=resource_cfg)
    return processed_args


class ResourceType(object):

    @classmethod
    @abc.abstractmethod
    def transform(cls, clients, resource_config):
        """Transform the resource.

        :param clients: openstack admin client handles
        :param resource_config: scenario config of resource

        :returns: transformed value of resource
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
        # In a case of pattern string exactly maches resource name
        matching_exact = filter(lambda r: r.name == resource_config["name"],
                                resources)
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
    matching = filter(lambda resource: re.search(pattern, resource.name),
                      resources)
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


def _id_from_name(resource_config, resources, typename):
    """Return the id of the resource whose name matches the pattern.

    resource_config has to contain `name`, as it is used to lookup an id.
    Value of the name will be treated as regexp.

    An `InvalidScenarioArgument` is thrown if the pattern does
    not match unambiguously.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource id uniquely mapped to `name` or `regex`
    """
    return obj_from_name(resource_config, resources, typename).id


class FlavorResourceType(ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get('id')
        if not resource_id:
            novaclient = clients.nova()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=novaclient.flavors.list(),
                                        typename='flavor')
        return resource_id


class ImageResourceType(ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get('id')
        if not resource_id:
            glanceclient = clients.glance()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=list(
                                            glanceclient.images.list()),
                                        typename='image')
        return resource_id


class VolumeTypeResourceType(ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get('id')
        if not resource_id:
            cinderclient = clients.cinder()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=cinderclient.
                                        volume_types.list(),
                                        typename='volume_type')
        return resource_id


class NeutronNetworkResourceType(ResourceType):

    @classmethod
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get('id')
        if resource_id:
            return resource_id
        else:
            neutronclient = clients.neutron()
            for net in neutronclient.list_networks()["networks"]:
                if net["name"] == resource_config.get("name"):
                    return net["id"]

        raise exceptions.InvalidScenarioArgument(
            "Neutron network with name '{name}' not found".format(
                name=resource_config.get("name")))
