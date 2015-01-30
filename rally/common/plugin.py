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

from rally.common import utils
from rally import exceptions


def deprecated(reason, rally_version):
    """Put this decorator on function or class to mark plugin as deprecated.

    :param reason: Message that describes why plugin was deprecated
    :param rally_version: version of Rally when this plugin was deprecated
    """
    def wrapper(plugin):
        plugin._plugin_deprecated = {
            "reason": reason,
            "rally_version": rally_version
        }
        return plugin

    return wrapper


def plugin(name):
    """Put this decorator on top of plugin to specify it's name.

    This will be used for everything except Scenarios plugins. They have
    different nature.

    :param name: name of plugin that is used for searching purpose
    """

    def wrapper(plugin):
        plugin._plugin_name = name
        return plugin

    return wrapper


class Plugin(object):
    """Use this class as a base for all plugins in Rally."""

    @classmethod
    def get_name(cls):
        return getattr(cls, "_plugin_name", None)

    @classmethod
    def get(cls, name):
        for _plugin in cls.get_all():
            if _plugin.get_name() == name:
                return _plugin

        raise exceptions.NoSuchPlugin(name=name)

    @classmethod
    def get_all(cls):
        return list(utils.itersubclasses(cls))

    @classmethod
    def is_deprecated(cls):
        """Return deprecation details for deprecated plugins."""
        return getattr(cls, "_plugin_deprecated", False)
