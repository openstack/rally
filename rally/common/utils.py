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
import inspect
import multiprocessing
import random
import string
import sys
import time

from six import moves

from rally.common.i18n import _
from rally.common import log as logging
from rally import exceptions

LOG = logging.getLogger(__name__)


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
        for k, v in moves.map(lambda x: (x, getattr(self, x)), dir(self)):
            if not k.startswith("_"):
                yield v


class StdOutCapture(object):
    def __init__(self):
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = moves.StringIO()
        return sys.stdout

    def __exit__(self, type, value, traceback):
        sys.stdout = self.stdout


class StdErrCapture(object):
    def __init__(self):
        self.stderr = sys.stderr

    def __enter__(self):
        sys.stderr = moves.StringIO()
        return sys.stderr

    def __exit__(self, type, value, traceback):
        sys.stderr = self.stderr


class Timer(object):
    def __enter__(self):
        self.error = None
        self.start = time.time()
        return self

    def timestamp(self):
        return self.start

    def __exit__(self, type, value, tb):
        self.finish = time.time()
        if type:
            self.error = (type, value, tb)

    def duration(self):
        return self.finish - self.start


class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


class RAMInt(object):
    """Share RAM integer, for IPC.

    This class represents iterable which refers directly to an integer value
    stored in RAM. Being a true system-level singletone, this allows safely
    share integer among processes and threads.
    """

    def __init__(self):
        self.__lock = multiprocessing.Lock()
        self.__int = multiprocessing.Value("I", 0)

    def __int__(self):
        return self.__int.value

    def __str__(self):
        return str(self.__int.value)

    def __iter__(self):
        return self

    def __next__(self):
        with self.__lock:
            value = self.__int.value
            self.__int.value += 1
            if self.__int.value > value:
                return value
            raise StopIteration

    def next(self):
        return self.__next__()

    def reset(self):
        with self.__lock:
            self.__int.value = 0


def _log_wrapper(obj, log_function, msg, **kw):
    """A logging wrapper for any method of a class.

    Class instances that use this decorator should have self.task or
    self.deployment attribute. The wrapper produces logs messages both
    before and after the method execution, in the following format
    (example for tasks):

    "Task <Task UUID> | Starting:  <Logging message>"
    [Method execution...]
    "Task <Task UUID> | Completed: <Logging message>"

    :param obj: task or deployment which must be attribute of "self"
    :param log_function: Logging method to be used, e.g. LOG.info
    :param msg: Text message (possibly parameterized) to be put to the log
    :param **kw: Parameters for msg
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            params = {"msg": msg % kw, "obj_name": obj.title(),
                      "uuid": getattr(self, obj)["uuid"]}
            log_function(_("%(obj_name)s %(uuid)s | Starting:  %(msg)s") %
                         params)
            result = f(self, *args, **kwargs)
            log_function(_("%(obj_name)s %(uuid)s | Completed: %(msg)s") %
                         params)
            return result
        return wrapper
    return decorator


def log_task_wrapper(log_function, msg, **kw):
    return _log_wrapper("task", log_function, msg, **kw)


def log_deploy_wrapper(log_function, msg, **kw):
    return _log_wrapper("deployment", log_function, msg, **kw)


def log_verification_wrapper(log_function, msg, **kw):
    return _log_wrapper("verification", log_function, msg, **kw)


def log_deprecated(message, rally_version, log_function=None):
    """A wrapper marking a certain method as deprecated.

    :param message: Message that describes why the method was deprecated
    :param rally_version: version of Rally when the method was deprecated
    :param log_function: Logging method to be used, e.g. LOG.info
    """
    log_function = log_function or LOG.warning

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            log_function("%(msg)s (deprecated in Rally v%(version)s)" %
                         {"msg": message, "version": rally_version})
            result = f(*args, **kwargs)
            return result
        return wrapper
    return decorator


def log_deprecated_args(message, rally_version, deprecated_args,
                        log_function=None, once=False):
    """A wrapper marking certain arguments as deprecated.

    :param message: Message that describes why the arguments were deprecated
    :param rally_version: version of Rally when the arguments were deprecated
    :param deprecated_args: List of deprecated args.
    :param log_function: Logging method to be used, e.g. LOG.info
    :param once: Show only once (default is each)
    """
    log_function = log_function or LOG.warning

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if (not once) or (not getattr(f, "_warned_dep_args", False)):
                deprecated = ", ".join([
                    "`%s'" % x for x in deprecated_args if x in kwargs])
                if deprecated:
                    log_function(
                        "%(msg)s (args %(args)s deprecated in Rally "
                        "v%(version)s)" %
                        {"msg": message, "version": rally_version,
                         "args": deprecated})
                    setattr(f, "_warned_dep_args", once)
            result = f(*args, **kwargs)
            return result
        return wrapper
    return decorator


def get_method_class(func):
    """Return the class that defined the given method.

    :param func: function to get the class for.
    :returns: class object or None if func is not an instance method.
    """
    if hasattr(func, "im_class"):
        # this check works in Python 2
        for cls in inspect.getmro(func.im_class):
            if func.__name__ in cls.__dict__:
                return cls
    elif hasattr(func, "__qualname__") and inspect.isfunction(func):
        # this check works in Python 3
        cls = getattr(
            inspect.getmodule(func),
            func.__qualname__.split(".<locals>.", 1)[0].rsplit(".", 1)[0])
        if isinstance(cls, type):
            return cls
    else:
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
        for x in moves.range(1, len(s1) + 1):
            n.append(min(l[x] + 1, n[-1] + 1,
                         l[x - 1] + (s2[y - 1] != s1[x - 1])))
    return n[-1]


def retry(times, func, *args, **kwargs):
    """Try to execute multiple times function mitigating exceptions.

    :param times: Amount of attempts to execute function
    :param func: Function that should be executed
    :param args: *args that are passed to func
    :param kwargs: **kwargs that are passed to func

    :raises: Raise any exception that can raise func
    :returns: Result of func(*args, **kwargs)
    """

    for i in range(times):
        try:
            return func(*args, **kwargs)
        except Exception:
            if i == times - 1:
                raise


def iterate_per_tenants(users):
    """Iterate of a single arbitrary user from each tenant

    :type users: list of users
    :return: iterator of a single user from each tenant
    """
    processed_tenants = set()
    for user in users:
        if user["tenant_id"] not in processed_tenants:
            processed_tenants.add(user["tenant_id"])
            yield (user, user["tenant_id"])

# NOTE(andreykurilin): Actually, this variable should be named as
# "_ASCII_LETTERS_AND_DIGITS", but since world is not ideal, name of variable
# can be non-ideal too.
_DIGITS_AND_ASCII_LETTERS = string.ascii_letters + string.digits


def generate_random_name(prefix="", length=16,
                         choice=_DIGITS_AND_ASCII_LETTERS):
    """Generates pseudo random name.

    :param prefix: str, custom prefix for random name
    :param length: int, length of random name
    :param choice: str, chars for random choice
    :returns: str, pseudo random name
    """

    rand_part = "".join(random.choice(choice) for i in range(length))
    return prefix + rand_part
