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

import imp
import importlib
import os
import pkg_resources
import pkgutil
import sys

import six

import rally
from rally.common import logging

LOG = logging.getLogger(__name__)


def itersubclasses(cls, seen=None):
    """Generator over all subclasses of a given class in depth first order.

    NOTE: Use 'seen' to exclude cls which was reduplicated found, because
    cls maybe has multiple super classes of the same plugin.
    """

    seen = seen or set()
    try:
        subs = cls.__subclasses__()
    except TypeError:   # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in seen:
            seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, seen):
                yield sub


def import_modules_from_package(package):
    """Import modules from package and append into sys.modules

    :param package: Full package name. For example: rally.plugins.openstack
    """
    path = [os.path.dirname(rally.__file__), ".."] + package.split(".")
    path = os.path.join(*path)
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.startswith("__") or not filename.endswith(".py"):
                continue
            new_package = ".".join(root.split(os.sep)).split("....")[1]
            module_name = "%s.%s" % (new_package, filename[:-3])
            if module_name not in sys.modules:
                sys.modules[module_name] = importlib.import_module(module_name)


def find_packages_by_entry_point():
    """Find all packages with rally_plugins entry-point"""
    loaded_packages = []

    for package in pkg_resources.working_set:
        entry_map = package.get_entry_map("rally_plugins")
        if not entry_map:
            # this package doesn't have rally_plugins entry-point
            continue

        package_info = {}

        if "path" in entry_map:
            ep = entry_map["path"]
            package_info["plugins_path"] = ep.module_name
        if "options" in entry_map:
            ep = entry_map["options"]
            package_info["options"] = "%s:%s" % (
                ep.module_name,
                ep.attrs[0] if ep.attrs else "list_opts",
            )

        if package_info:
            package_info.update(
                name=package.project_name,
                version=package.version)
            loaded_packages.append(package_info)
    return loaded_packages


def import_modules_by_entry_point(_packages=None):
    """Import plugins by entry-point 'rally_plugins'."""
    loaded_packages = _packages or find_packages_by_entry_point()

    for package in loaded_packages:
        if "plugins_path" in package:
            em = pkg_resources.get_entry_map(package["name"])
            ep = em["rally_plugins"]["path"]
            try:
                m = ep.load()
                if hasattr(m, "__path__"):
                    path = pkgutil.extend_path(m.__path__, m.__name__)
                else:
                    path = [m.__file__]
                prefix = m.__name__ + "."
                for loader, name, _is_pkg in pkgutil.walk_packages(
                        path, prefix=prefix):
                    sys.modules[name] = importlib.import_module(name)
            except Exception as e:
                msg = ("\t Failed to load plugins from module '%(module)s' "
                       "(package: '%(package)s')" %
                       {"module": ep.module_name,
                        "package": "%s %s" % (package["name"],
                                              package["version"])})
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg + (": %s" % six.text_type(e)))
    return loaded_packages


def load_plugins(dir_or_file):
    if os.path.isdir(dir_or_file):
        directory = dir_or_file
        LOG.info("Loading plugins from directories %s/*" %
                 directory.rstrip("/"))

        to_load = []
        for root, dirs, files in os.walk(directory, followlinks=True):
            to_load.extend((plugin[:-3], root)
                           for plugin in files if plugin.endswith(".py"))
        for plugin, directory in to_load:
            if directory not in sys.path:
                sys.path.append(directory)

            fullpath = os.path.join(directory, plugin)
            try:
                fp, pathname, descr = imp.find_module(plugin, [directory])
                imp.load_module(plugin, fp, pathname, descr)
                fp.close()
                LOG.info("\t Loaded module with plugins: %s.py" % fullpath)
            except Exception as e:
                msg = "\t Failed to load module with plugins %s.py" % fullpath
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning("%(msg)s: %(e)s" % {"msg": msg, "e": e})
    elif os.path.isfile(dir_or_file) and dir_or_file.endswith(".py"):
        plugin_file = dir_or_file
        LOG.info("Loading plugins from file %s" % plugin_file)
        if plugin_file not in sys.path:
            sys.path.append(plugin_file)
        try:
            plugin_name = os.path.splitext(plugin_file.split("/")[-1])[0]
            imp.load_source(plugin_name, plugin_file)
            LOG.info("\t Loaded module with plugins: %s.py" % plugin_name)
        except Exception as e:
            msg = "\t Failed to load module with plugins %s" % plugin_file
            if logging.is_debug():
                LOG.exception(msg)
            else:
                LOG.warning("%(msg)s: %(e)s" % {"msg": msg, "e": e})
