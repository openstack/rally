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

import importlib
import importlib.metadata
import importlib.util
import os
import pkgutil
import sys
import typing as t

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
    path = [os.path.dirname(rally.__file__), "..", *package.split(".")]
    path = os.path.join(*path)
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.startswith("__") or not filename.endswith(".py"):
                continue
            new_package = ".".join(root.split(os.sep)).split("....")[1]
            module_name = "%s.%s" % (new_package, filename[:-3])
            if module_name not in sys.modules:
                sys.modules[module_name] = importlib.import_module(module_name)


def iter_entry_points():  # pragma: no cover
    try:
        # Python 3.10+
        return importlib.metadata.entry_points(group="rally_plugins")
    except TypeError:
        # Python 3.8-3.9
        return importlib.metadata.entry_points().get("rally_plugins", [])


def find_packages_by_entry_point():
    """Find all packages with rally_plugins entry-point"""
    packages = {}

    for ep in iter_entry_points():
        if ep.name not in ("path", "options"):
            continue
        if ep.dist.name not in packages:
            packages[ep.dist.name] = {
                "name": ep.dist.name,
                "version": ep.dist.version
            }

        if ep.name == "path":
            packages[ep.dist.name]["plugins_path"] = ep.value
            packages[ep.dist.name]["plugins_path_ep"] = ep
        elif ep.name == "options":
            packages[ep.dist.name]["options"] = (
                ep.value if ":" in ep.value else f"{ep.value}:list_opts"
            )

    return list(packages.values())


def import_modules_by_entry_point(_packages: t.Union[list, None] = None):
    """Import plugins by entry-point 'rally_plugins'."""
    if _packages is not None:
        loaded_packages = _packages
    else:
        loaded_packages = find_packages_by_entry_point()

    for package in loaded_packages:
        if "plugins_path" in package:

            ep = package["plugins_path_ep"]
            try:
                m = ep.load()
                if hasattr(m, "__path__"):
                    path = pkgutil.extend_path(m.__path__, m.__name__)
                else:
                    path = [m.__file__]
                prefix = m.__name__ + "."
                for loader, name, _is_pkg in pkgutil.walk_packages(
                        path, prefix=prefix):
                    if name not in sys.modules:
                        sys.modules[name] = importlib.import_module(name)
            except Exception as e:
                msg = ("\t Failed to load plugins from module '%(module)s' "
                       "(package: '%(package)s')" %
                       {"module": ep.name,
                        "package": "%s %s" % (package["name"],
                                              package["version"])})
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg + (": %s" % str(e)))
    return loaded_packages


_loaded_modules = []


def load_plugins(dir_or_file, depth=0):
    if os.path.isdir(dir_or_file):
        directory = dir_or_file
        LOG.info("Loading plugins from directories %s/*" %
                 directory.rstrip("/"))
        for root, _dirs, files in os.walk(directory, followlinks=True):
            if root not in sys.path:
                # this hack is required to support relative imports
                sys.path.append(root)

            for plugin in files:
                load_plugins(os.path.join(root, plugin), depth=1)

    elif os.path.isfile(dir_or_file) and dir_or_file.endswith(".py"):
        plugin_file = dir_or_file
        msg = "Loading plugins from file %s" % plugin_file
        if depth:
            msg = "\t" + msg
        LOG.info(msg)
        module_name = os.path.splitext(os.path.basename(plugin_file))[0]
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        except Exception as e:
            msg = "\t Failed to load module with plugins %s" % plugin_file
            if logging.is_debug():
                LOG.exception(msg)
            else:
                LOG.warning("%(msg)s: %(e)s" % {"msg": msg, "e": e})
            return
        _loaded_modules.append(module)
        LOG.info("\t Loaded module with plugins: %s" % module_name)
