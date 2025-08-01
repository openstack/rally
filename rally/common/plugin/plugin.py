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

from __future__ import annotations

import sys
import typing as t

from rally.common.plugin import discover
from rally.common.plugin import info
from rally.common.plugin import meta
from rally import exceptions


if t.TYPE_CHECKING:  # pragma: no cover
    P = t.TypeVar("P", bound="Plugin")


class DeprecationInfo(t.TypedDict):
    """Structure for plugin deprecation information."""
    reason: str
    rally_version: str


def base() -> t.Callable[[type[P]], type[P]]:
    """Mark Plugin as a base.

    Base Plugins are used to have better organization of plugins providing
    subtypes. Base Plugins may contain documentation and other base methods
    related to specific type of plugins, resolving next problems:

    - Having different types of plugins (e.g. Scenario, Context, SLA, ...)
    - Auto generation of plugin reference with splitting plugins by their base
    - Plugin lookup - one can easily get all plugins from some base.

    Plugin bases by default initialize _default_meta
    """
    def wrapper(cls: type[P]) -> type[P]:
        if not issubclass(cls, Plugin):
            raise exceptions.RallyException(
                "Plugin's Base can be only a subclass of Plugin class.")

        parent = cls._get_base()
        if parent != Plugin:
            raise exceptions.RallyException(
                "'%(plugin_cls)s' can not be marked as plugin base, since it "
                "inherits from '%(parent)s' which is also plugin base."
                % {"plugin_cls": cls.__name__, "parent": parent.__name__})

        cls.base_ref = cls
        cls._default_meta_init(True)
        return cls
    return wrapper


def configure(
    name: str, platform: str = "default", hidden: bool = False
) -> t.Callable[[type[P]], type[P]]:
    """Use this decorator to configure plugin's attributes.

    Plugin is not discoverable until configure() is performed.

    :param name: name of plugin that is used for searching purpose
    :param platform: platform name that plugin belongs to
    :param hidden: if True the plugin will be marked as hidden and can be
        loaded only explicitly
    """

    def decorator(plugin: type[P]) -> type[P]:
        plugin_id = "%s.%s" % (plugin.__module__, plugin.__name__)
        if not name:
            raise ValueError(
                f"The name of the plugin {plugin_id} cannot be empty.")
        if "@" in name:
            raise ValueError(
                f"The name of the plugin {plugin_id} cannot contain @ symbol")

        plugin._meta_init()
        try:
            existing_plugin = plugin._get_base().get(
                name=name, platform=platform, allow_hidden=True)
        except exceptions.PluginNotFound:
            plugin._meta_set("name", name)
            plugin._meta_set("platform", platform)
        else:
            plugin.unregister()
            raise exceptions.PluginWithSuchNameExists(
                name=name, platform=existing_plugin.get_platform(),
                existing_path=(
                    sys.modules[existing_plugin.__module__].__file__),
                new_path=sys.modules[plugin.__module__].__file__
            )
        plugin._meta_set("hidden", hidden)
        return plugin

    return decorator


def default_meta(inherit: bool = True) -> t.Callable[[type[P]], type[P]]:
    """Initialize default meta for particular plugin.

    Default Meta is inherited by all children comparing to Meta which is unique
    per plugin.

    :param inherit: Whatever to copy parents default meta
    """

    def decorator(plugin: type[P]) -> type[P]:
        plugin._default_meta_init(inherit)
        return plugin

    return decorator


def deprecated(
    reason: str, rally_version: str
) -> t.Callable[[type[P]], type[P]]:
    """Mark plugin as deprecated.

    :param reason: Message that describes reason of plugin deprecation
    :param rally_version: Deprecated since this version of Rally
    """
    def decorator(plugin: type[P]) -> type[P]:
        plugin._meta_set("deprecated", dict(
            reason=reason,
            rally_version=rally_version
        ))
        return plugin

    return decorator


class Plugin(meta.MetaMixin, info.InfoMixin):
    """Base class for all Plugins in Rally."""

    base_ref: t.ClassVar[type[Plugin]]  # Dynamically set by @base() decorator

    @classmethod
    def unregister(cls) -> None:
        """Removes all plugin meta information and makes it undiscoverable."""
        cls._meta_clear()

    @classmethod
    def _get_base(cls) -> type[Plugin]:
        return getattr(cls, "base_ref", Plugin)

    @classmethod
    def get(
        cls: type[P],
        name: str,
        platform: str | None = None,
        allow_hidden: bool = False
    ) -> type[P]:
        """Return plugin by its name for specified platform.

        :param name: Plugin's name or fullname
        :param platform: Plugin's platform
        :param allow_hidden: if False and found plugin is hidden then
                              PluginNotFound is raised
        """
        if "@" in name:
            name, platform = name.split("@", 1)

        results = cls.get_all(name=name, platform=platform,
                              allow_hidden=allow_hidden)

        if not results:
            base = cls._get_base()
            base = "" if base == Plugin else " %s" % base.__name__
            raise exceptions.PluginNotFound(
                name=name, platform=platform or "any", base=base)

        if len(results) == 1:
            return results[0]

        if platform is None:
            # try to use default platform
            default = [p for p in results if p.get_platform() == "default"]
            if default:
                return default[0]

        raise exceptions.MultiplePluginsFound(
            name=name,
            plugins=", ".join(p.get_fullname() for p in results))

    @classmethod
    def get_all(
        cls: type[P],
        platform: str | None = None,
        allow_hidden: bool = False,
        name: str | None = None,
    ) -> list[type[P]]:
        """Return all subclass plugins of plugin.

        All plugins that are not configured will be ignored.
        :param platform: return only plugins for specific platform.
        :param name: return only plugins with specified name.
        :param allow_hidden: if False return only non hidden plugins
        """
        plugins = []

        for p in discover.itersubclasses(cls):
            if not issubclass(p, Plugin):
                continue
            if not p._meta_is_inited(raise_exc=False):
                continue
            if name and name != p.get_name():
                continue
            if platform and platform != p.get_platform():
                continue
            if not allow_hidden and p.is_hidden():
                continue
            plugins.append(p)

        return plugins

    @classmethod
    def get_name(cls) -> str:
        """Return plugin's name."""
        return cls._meta_get("name")

    @classmethod
    def get_platform(cls) -> str:
        """"Return plugin's platform name."""
        return cls._meta_get("platform")

    @classmethod
    def get_fullname(cls) -> str:
        """Returns plugins's full name."""
        return "%s@%s" % (cls.get_name(), cls.get_platform() or "")

    @classmethod
    def is_hidden(cls) -> bool:
        """Returns whatever plugin is hidden or not."""
        return cls._meta_get("hidden", False)

    @classmethod
    def is_deprecated(cls) -> DeprecationInfo | t.Literal[False]:
        """Returns deprecation details if plugin is deprecated."""
        return cls._meta_get("deprecated", False)
