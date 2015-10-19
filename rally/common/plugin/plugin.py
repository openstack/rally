# Copyright 2015: Mirantis Inc.
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

import sys

from rally.common.i18n import _LE
from rally.common.plugin import discover
from rally.common.plugin import info
from rally.common.plugin import meta
from rally import exceptions


def deprecated(reason, rally_version):
    """Mark plugin as deprecated.

    :param reason: Message that describes reason of plugin deprecation
    :param rally_version: Deprecated since this version of Rally
    """
    def decorator(plugin):
        plugin._set_deprecated(reason, rally_version)
        return plugin

    return decorator


def base():
    """Mark Plugin as a base.

    .. warning:: This decorator should be added the line before
        six.add_metaclass if it is used.
    """
    def wrapper(cls):
        if not issubclass(cls, Plugin):
            raise exceptions.RallyException(_LE(
                "Plugin's Base can be only a subclass of Plugin class."))

        parent = cls._get_base()
        if parent != Plugin:
            raise exceptions.RallyException(_LE(
                "'%(plugin_cls)s' can not be marked as plugin base, since it "
                "inherits from '%(parent)s' which is also plugin base.") % {
                "plugin_cls": cls.__name__,
                "parent": parent.__name__})

        cls.base_ref = cls
        return cls
    return wrapper


def configure(name, namespace="default"):
    """Use this decorator to configure plugin's attributes.

    :param name: name of plugin that is used for searching purpose
    :param namespace: plugin namespace
    """

    def decorator(plugin):
        plugin._configure(name, namespace)
        return plugin

    return decorator


def from_func(plugin_baseclass=None):
    """Add all plugin's methods to function object.

    Rally benchmark scenarios are different from all other plugins in Rally.

    Usually 1 plugin is 1 class and we can easily use Plugin() as base for
    all of them to avoid code duplication. In case of benchmark scenarios
    1 class can contain any amount of scenarios that are just methods
    of this class.

    To make Rally code cleaner these methods should look/work like other
    Plugins.

    This decorator makes all dirty work for us, it creates dynamically new
    class, adds plugin instance and aliases for all non-private methods of
    Plugin instance to passed function.


    For example,

    @plugin.from_func()
    def my_plugin_like_func(a, b):
        pass


    assert my_plugin_like_func.get_name() == "my_plugin_like_func"
    assert my_plugin_like_func.get_all() == []


    As a result, adding plugin behavior for benchmark scenarios fully unifies
    work with benchmark scenarios and other kinds of plugins.

    :param plugin_baseclass: if specified, subclass of this class will be used
                             to add behavior of plugin to function else,
                             subclass of Plugin will be used.
    :returns: Function decorator that adds plugin behavior to function
    """

    if plugin_baseclass:
        if not issubclass(plugin_baseclass, Plugin):
            raise TypeError("plugin_baseclass should be subclass of %s "
                            % Plugin)

        class FuncPlugin(plugin_baseclass):
            pass

    else:
        class FuncPlugin(Plugin):
            pass

    def decorator(func):
        func._plugin = FuncPlugin

        # NOTE(boris-42): This is required by Plugin.get_all method to
        #                 return func instead of FuncPlugin that will be
        #                 auto discovered.
        FuncPlugin.func_ref = func

        # NOTE(boris-42): Make aliases from func to all public Plugin fields
        for field in dir(func._plugin):
            if not field.startswith("__"):
                obj = getattr(func._plugin, field)
                if callable(obj):
                    setattr(func, field, obj)

        return func

    return decorator


class Plugin(meta.MetaMixin, info.InfoMixin):
    """Base class for all Plugins in Rally."""

    @classmethod
    def _configure(cls, name, namespace="default"):
        """Init plugin and set common meta information.

        For now it sets only name of plugin, that is actually identifier.
        Plugin name should be unique, otherwise exception is raised.

        :param name: Plugin name
        :param namespace: Plugins with the same name are allowed only if they
                          are in various namespaces.
        """
        cls._meta_init()
        cls._set_name_and_namespace(name, namespace)
        return cls

    @classmethod
    def unregister(cls):
        """Removes all plugin meta information and makes it undiscoverable."""
        cls._meta_clear()

    @classmethod
    def _get_base(cls):
        return getattr(cls, "base_ref", Plugin)

    @classmethod
    def _set_name_and_namespace(cls, name, namespace):
        try:
            existing_plugin = cls._get_base().get(name=name,
                                                  namespace=namespace)

        except exceptions.PluginNotFound:
            cls._meta_set("name", name)
            cls._meta_set("namespace", namespace)
        else:
            raise exceptions.PluginWithSuchNameExists(
                name=name, namespace=namespace,
                existing_path=(
                    sys.modules[existing_plugin.__module__].__file__),
                new_path=sys.modules[cls.__module__].__file__
            )

    @classmethod
    def _set_deprecated(cls, reason, rally_version):
        """Mark plugin as deprecated.

        :param reason: Message that describes reason of plugin deprecation
        :param rally_version: Deprecated since this version of Rally
        """

        cls._meta_set("deprecated", {
            "reason": reason,
            "rally_version": rally_version
        })
        return cls

    @classmethod
    def get(cls, name, namespace=None):
        """Return plugin by its name from specified namespace.

        This method iterates over all subclasses of cls and returns plugin
        by name from specified namespace.

        If namespace is not specified it will return first found plugin from
        any of namespaces.

        :param name: Plugin's name
        :param namespace: Namespace where to search for plugins
        """
        potential_result = []

        for p in cls.get_all(namespace=namespace):
            if p.get_name() == name:
                potential_result.append(p)

        if len(potential_result) == 1:
            return potential_result[0]
        elif potential_result:
            hint = _LE("Try to choose the correct Plugin base or namespace to "
                       "search in.")
            if namespace:
                needle = "%s at %s namespace" % (name, namespace)
            else:
                needle = "%s at any of namespaces" % name
            raise exceptions.MultipleMatchesFound(
                needle=needle,
                haystack=", ".join(p.get_name() for p in potential_result),
                hint=hint)

        raise exceptions.PluginNotFound(
            name=name, namespace=namespace or "any of")

    @classmethod
    def get_all(cls, namespace=None):
        """Return all subclass plugins of plugin.

        All plugins that are not configured will be ignored.

        :param namespace: return only plugins from specified namespace.
        """
        plugins = []

        for p in discover.itersubclasses(cls):
            if issubclass(p, Plugin) and p._meta_is_inited(raise_exc=False):
                if not namespace or namespace == p.get_namespace():
                    plugins.append(getattr(p, "func_ref", p))

        return plugins

    @classmethod
    def get_name(cls):
        """Return name of plugin."""
        return cls._meta_get("name")

    @classmethod
    def get_namespace(cls):
        """"Return namespace of plugin, e.g. default or openstack."""
        return cls._meta_get("namespace")

    @classmethod
    def is_deprecated(cls):
        """Return deprecation details for deprecated plugins."""
        return cls._meta_get("deprecated", False)
