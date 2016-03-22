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
import os.path
import re

import requests

from rally.common.i18n import _
from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions
from rally import osclients
from rally.task import scenario

LOG = logging.getLogger(__name__)


@logging.log_deprecated("Use types.convert() instead", "0.3.2", once=True)
def set(**kwargs):
    """Decorator to define resource transformation(s) on scenario parameters.

    The `kwargs` passed as arguments to the decorator are used to
    map a key in the scenario config to the subclass of ResourceType
    used to perform a transformation on the value of that key.
    """
    def wrapper(func):
        func._meta_setdefault("preprocessors", {})
        func._meta_get("preprocessors").update(kwargs)
        return func
    return wrapper


def _get_preprocessor_loader(plugin_name):
    """Get a class that loads a preprocessor class.

    This returns a class with a single class method, ``transform``,
    which, when called, finds a plugin and defers to its ``transform``
    class method. This is necessary because ``convert()`` is called as
    a decorator at import time, but we cannot be confident that the
    ResourceType plugins may not be loaded yet. (In fact, since
    ``convert()`` is used to decorate plugins, we can be confident
    that not all plugins are loaded when it is called.)

    This permits us to defer plugin searching until the moment when
    ``preprocess()`` calls the various preprocessors, at which point
    we can be certain that all plugins have been loaded and finding
    them by name will work.
    """
    # NOTE(stpierre): This technically doesn't work, because
    # ResourceType subclasses aren't plugins (yet)
    def transform(cls, *args, **kwargs):
        plug = ResourceType.get(plugin_name)
        return plug.transform(*args, **kwargs)

    return type("PluginLoader_%s" % plugin_name,
                (object,),
                {"transform": classmethod(transform)})


def convert(**kwargs):
    """Decorator to define resource transformation(s) on scenario parameters.

    This will eventually replace set(). For the time being, set()
    should be preferred.

    The ``kwargs`` passed as arguments are used to map a key in the
    scenario config to the resource type plugin used to perform a
    transformation on the value of the key. For instance:

        @types.convert(image={"type": "glance_image"})

    This would convert the ``image`` key in the scenario configuration
    to a Glance image by using the ``glance_image`` resource
    plugin. Currently ``type`` is the only recognized key, but others
    may be added in the future.
    """
    preprocessors = dict([(k, _get_preprocessor_loader(v["type"]))
                          for k, v in kwargs.items()])

    def wrapper(func):
        func._meta_setdefault("preprocessors", {})
        func._meta_get("preprocessors").update(preprocessors)
        return func
    return wrapper


def preprocess(name, context, args):
    """Run preprocessor on scenario arguments.

    :param name: Plugin name
    :param context: dictionary object that must have admin and credential
                    entries
    :param args: args section of benchmark specification in rally task file

    :returns processed_args: dictionary object with additional client
                             and resource configuration

    """
    preprocessors = scenario.Scenario.get(name)._meta_get("preprocessors",
                                                          default={})
    clients = osclients.Clients(context["admin"]["credential"])
    processed_args = copy.deepcopy(args)

    for src, preprocessor in preprocessors.items():
        resource_cfg = processed_args.get(src)
        if resource_cfg:
            processed_args[src] = preprocessor.transform(
                clients=clients, resource_config=resource_cfg)
    return processed_args


class ResourceType(plugin.Plugin):

    @classmethod
    @abc.abstractmethod
    def transform(cls, clients, resource_config):
        """Transform the resource.

        :param clients: openstack admin client handles
        :param resource_config: scenario config of resource

        :returns: transformed value of resource
        """


class DeprecatedResourceType(object):

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
                if re.search(pattern, resource.name)]
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
        elif len(matching) > 1:
            raise exceptions.MultipleMatchesFound(
                needle="{typename} with id '{id}'".format(
                    typename=typename.title(), id=resource_config["id"]),
                haystack=matching)
        else:
            raise exceptions.InvalidScenarioArgument(
                "{typename} with id '{id}' not found".format(
                    typename=typename.title(), id=resource_config["id"]))
    else:
        raise exceptions.InvalidScenarioArgument(
            "{typename} 'id' not found in '{resource_config}'".format(
                typename=typename.title(), resource_config=resource_config))


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


def _name_from_id(resource_config, resources, typename):
    """Return the name of the resource which has the id.

    resource_config has to contain `id`, as it is used to lookup a name.

    :param resource_config: resource to be transformed
    :param resources: iterable containing all resources
    :param typename: name which describes the type of resource

    :returns: resource name mapped to `id`
    """
    return obj_from_id(resource_config, resources, typename).name


def log_deprecated_resource_type(func):
    """Decorator that logs use of deprecated resource type classes.

    This should only be used on the transform() function.
    """
    def inner(cls, clients, resource_config):
        LOG.warning(_("%s is deprecated in Rally v0.3.2; use the "
                      "equivalent resource plugin name instead") %
                    cls.__name__)
        return func(cls, clients, resource_config)

    return inner


class FlavorResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            novaclient = clients.nova()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=novaclient.flavors.list(),
                                        typename="flavor")
        return resource_id


class EC2FlavorResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to name.

        In the case of using EC2 API, flavor name is used for launching
        servers.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: name matching resource
        """
        resource_name = resource_config.get("name")
        if not resource_name:
            # NOTE(wtakase): gets resource name from OpenStack id
            novaclient = clients.nova()
            resource_name = _name_from_id(resource_config=resource_config,
                                          resources=novaclient.flavors.list(),
                                          typename="flavor")
        return resource_name


class ImageResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            glanceclient = clients.glance()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=list(
                                            glanceclient.images.list()),
                                        typename="image")
        return resource_id


class EC2ImageResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to EC2 id.

        If OpenStack resource id is given, this function gets resource name
        from the id and then gets EC2 resource id from the name.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: EC2 id matching resource
        """
        if "name" not in resource_config and "regex" not in resource_config:
            # NOTE(wtakase): gets resource name from OpenStack id
            glanceclient = clients.glance()
            resource_name = _name_from_id(resource_config=resource_config,
                                          resources=list(
                                              glanceclient.images.list()),
                                          typename="image")
            resource_config["name"] = resource_name

        # NOTE(wtakase): gets EC2 resource id from name or regex
        ec2client = clients.ec2()
        resource_ec2_id = _id_from_name(resource_config=resource_config,
                                        resources=list(
                                            ec2client.get_all_images()),
                                        typename="ec2_image")
        return resource_ec2_id


class VolumeTypeResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
        if not resource_id:
            cinderclient = clients.cinder()
            resource_id = _id_from_name(resource_config=resource_config,
                                        resources=cinderclient.
                                        volume_types.list(),
                                        typename="volume_type")
        return resource_id


class NeutronNetworkResourceType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Transform the resource config to id.

        :param clients: openstack admin client handles
        :param resource_config: scenario config with `id`, `name` or `regex`

        :returns: id matching resource
        """
        resource_id = resource_config.get("id")
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


class FilePathOrUrlType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Check whether file exists or url available.

        :param clients: openstack admin client handles
        :param resource_config: path or url

        :returns: url or expanded file path
        """

        path = os.path.expanduser(resource_config)
        if os.path.isfile(path):
            return path
        try:
            head = requests.head(path)
            if head.status_code == 200:
                return path
            raise exceptions.InvalidScenarioArgument(
                "Url %s unavailable (code %s)" % (path, head.status_code))
        except Exception as ex:
            raise exceptions.InvalidScenarioArgument(
                "Url error %s (%s)" % (path, ex))


class FileType(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Return content of the file by its path.

        :param clients: openstack admin client handles
        :param resource_config: path to file

        :returns: content of the file
        """

        with open(os.path.expanduser(resource_config), "r") as f:
            return f.read()


class FileTypeDict(DeprecatedResourceType):

    @classmethod
    @log_deprecated_resource_type
    def transform(cls, clients, resource_config):
        """Return the dictionary of items with file path and file content.

        :param clients: openstack admin client handles
        :param resource_config: list of file paths

        :returns: dictionary {file_path: file_content, ...}
        """

        file_type_dict = {}
        for file_path in resource_config:
            file_path = os.path.expanduser(file_path)
            with open(file_path, "r") as f:
                file_type_dict[file_path] = f.read()

        return file_type_dict
