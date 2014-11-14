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

import functools
import imp
import inspect
import itertools
import os
import re
import StringIO
import sys
import time

from oslo.config import cfg
from oslo.utils import importutils
from sphinx.util import docstrings

from rally import exceptions
from rally.i18n import _
from rally import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

JSON_SCHEMA = 'http://json-schema.org/draft-04/schema'


class ImmutableMixin(object):
    _inited = False

    def __init__(self):
        self._inited = True

    def __setattr__(self, key, value):
        if self._inited:
            raise exceptions.ImmutableException()
        super(ImmutableMixin, self).__setattr__(key, value)


class EnumMixin(object):
    def __iter__(self):
        for k, v in itertools.imap(lambda x: (x, getattr(self, x)), dir(self)):
            if not k.startswith('_'):
                yield v


class StdOutCapture(object):
    def __init__(self):
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = StringIO.StringIO()
        return sys.stdout

    def __exit__(self, type, value, traceback):
        sys.stdout = self.stdout


class StdErrCapture(object):
    def __init__(self):
        self.stderr = sys.stderr

    def __enter__(self):
        sys.stderr = StringIO.StringIO()
        return sys.stderr

    def __exit__(self, type, value, traceback):
        sys.stderr = self.stderr


class Timer(object):
    def __enter__(self):
        self.error = None
        self.start = time.time()
        return self

    def __exit__(self, type, value, tb):
        self.finish = time.time()
        if type:
            self.error = (type, value, tb)

    def duration(self):
        return self.finish - self.start


class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


def itersubclasses(cls, _seen=None):
    """Generator over all subclasses of a given class in depth first order."""

    if not isinstance(cls, type):
        raise TypeError(_('itersubclasses must be called with '
                          'new-style classes, not %.100r') % cls)
    _seen = _seen or set()
    try:
        subs = cls.__subclasses__()
    except TypeError:   # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub


def try_append_module(name, modules):
    if name not in modules:
        modules[name] = importutils.import_module(name)


def import_modules_from_package(package):
    """Import modules from package and append into sys.modules

    :param: package - Full package name. For example: rally.deploy.engines
    """
    path = [os.path.dirname(__file__), '..'] + package.split('.')
    path = os.path.join(*path)
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.startswith('__') or not filename.endswith('.py'):
                continue
            new_package = ".".join(root.split(os.sep)).split("....")[1]
            module_name = '%s.%s' % (new_package, filename[:-3])
            try_append_module(module_name, sys.modules)


def _log_wrapper(obj, log, msg, **kw):
    """A logging wrapper for any method of a class.

    Class instances that use this decorator should have self.task or
    self.deployment attribute. The wrapper produces logs messages both
    before and after the method execution, in the following format
    (example for tasks):

    "Task <Task UUID> | Starting:  <Logging message>"
    [Method execution...]
    "Task <Task UUID> | Completed: <Logging message>"

    :param obj: task or deployment which must be attribute of 'self'
    :param log: Logging method to be used, e.g. LOG.info
    :param msg: Text message (possibly parameterized) to be put to the log
    :param **kw: Parameters for msg
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            params = {"msg": msg % kw, "obj_name": obj.title(),
                      "uuid": getattr(self, obj)["uuid"]}
            log(_("%(obj_name)s %(uuid)s | Starting:  %(msg)s") % params)
            result = f(self, *args, **kwargs)
            log(_("%(obj_name)s %(uuid)s | Completed: %(msg)s") % params)
            return result
        return wrapper
    return decorator


def log_task_wrapper(log, msg, **kw):
    return _log_wrapper('task', log, msg, **kw)


def log_deploy_wrapper(log, msg, **kw):
    return _log_wrapper('deployment', log, msg, **kw)


def log_verification_wrapper(log, msg, **kw):
    return _log_wrapper('verification', log, msg, **kw)


def load_plugins(directory):
    if os.path.exists(directory):
        LOG.info("Loading plugins from directories %s/*" % directory)

        to_load = []
        for root, dirs, files in os.walk(directory):
            to_load.extend((plugin[:-3], root)
                           for plugin in files if plugin.endswith(".py"))
        for plugin, directory in to_load:
            fullpath = os.path.join(directory, plugin)
            try:
                fp, pathname, descr = imp.find_module(plugin, [directory])
                imp.load_module(plugin, fp, pathname, descr)
                fp.close()
                LOG.info("\t Loaded module with plugins: %s.py" % fullpath)
            except Exception as e:
                LOG.warning(
                    "\t Failed to load module with plugins %(path)s.py: %(e)s"
                    % {"path": fullpath, "e": e})
                if CONF.debug:
                    LOG.exception(e)


def get_method_class(func):
    """Return the class that defined the given method.

    :param func: function to get the class for.
    :returns: class object or None if func is not an instance method.
    """
    if not hasattr(func, "im_class"):
        return None
    for cls in inspect.getmro(func.im_class):
        if func.__name__ in cls.__dict__:
            return cls
    return None


def first_index(lst, predicate):
    """Return the index of the first element that matches a predicate.

    :param lst: list to find the matching element in.
    :param predicate: predicate object.
    :returns: the index of the first matching element or None if no element
              matches the predicate.
    """
    for i in range(len(lst)):
        if predicate(lst[i]):
            return i
    return None


def format_docstring(docstring):
    """Format the docstring to make it well-readable.

    :param docstring: string.
    :returns: formatted string.
    """
    if docstring:
        return "\n".join(docstrings.prepare_docstring(docstring))
    else:
        return ""


def parse_docstring(docstring):
    """Parse the docstring into its components.

    :returns: a dictionary of form
              {
                  "short_description": ...,
                  "long_description": ...,
                  "params": [{"name": ..., "doc": ...}, ...],
                  "returns": ...
              }
    """

    if docstring:
        lines = docstrings.prepare_docstring(docstring)
        lines = filter(lambda line: line != "", lines)
    else:
        lines = []

    if lines:
        short_description = lines[0]

        param_start = first_index(lines, lambda l: l.startswith(":param"))
        returns_start = first_index(lines, lambda l: l.startswith(":returns"))
        if param_start or returns_start:
            description_end = param_start or returns_start
            long_description = "\n".join(lines[1:description_end])
        else:
            long_description = "\n".join(lines[1:])

        if not long_description:
            long_description = None

        param_lines = []
        if param_start:
            current_line = lines[param_start]
            current_line_index = param_start + 1
            while current_line_index < (returns_start or len(lines)):
                if lines[current_line_index].startswith(":param"):
                    param_lines.append(current_line)
                    current_line = lines[current_line_index]
                else:
                    continuation_line = lines[current_line_index].strip()
                    current_line += " " + continuation_line
                current_line_index += 1
            param_lines.append(current_line)
        params = []
        param_regex = re.compile("^:param (?P<name>\w+): (?P<doc>.*)$")
        for param_line in param_lines:
            match = param_regex.match(param_line)
            if match:
                params.append({
                    "name": match.group("name"),
                    "doc": match.group("doc")
                })

        returns = None
        if returns_start:
            returns_line = " ".join([l.strip() for l in lines[returns_start:]])
            returns_regex = re.compile("^:returns: (?P<doc>.*)$")
            match = returns_regex.match(returns_line)
            if match:
                returns = match.group("doc")

        return {
            "short_description": short_description,
            "long_description": long_description,
            "params": params,
            "returns": returns
        }

    else:
        return {
            "short_description": None,
            "long_description": None,
            "params": [],
            "returns": None
        }


def distance(s1, s2):
    """Computes the edit distance between two strings.

    The edit distance is the Levenshtein distance. The larger the return value,
    the more edits are required to transform one string into the other.

    :param s1: First string to compare
    :param s2: Second string to compare
    :returns: Integer distance between two strings
    """
    n = range(0, len(s1) + 1)
    for y in range(1, len(s2) + 1):
        l, n = n, [y]
        for x in xrange(1, len(s1) + 1):
            n.append(min(l[x] + 1, n[-1] + 1,
                         l[x - 1] + (s2[y - 1] != s1[x - 1])))
    return n[-1]


def retry(times, func, *args, **kwargs):
    """Tries to execute multiple times function mitigating exceptions.

    :param times: Amount of attempts to execute function
    :param func: Function that should be executed
    :param *args: *args that are passed to func
    :param **kwargs: **kwargs that are passed to func

    :raises: Raise any exception that can raise func
    :returns: Result of func(*args, **kwargs)
    """

    for i in range(times):
        try:
            return func(*args, **kwargs)
        except Exception:
            if i == times - 1:
                raise
