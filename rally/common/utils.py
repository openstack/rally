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

import bisect
import heapq
import inspect
import multiprocessing
import random
import re
import string
import sys
import time

from six import moves

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

    :raises Exception: Raise any exception that can raise func
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


_resource_name_placeholder_re = re.compile(
    "^(?P<prefix>.*?)(?P<task>X{3,})(?P<sep>[^X]+?)(?P<rand>X{3,})"
    "(?P<suffix>.*)$")


class RandomNameGeneratorMixin(object):
    """Mixin for objects that need to generate random names.

    This mixin provides one method,
    ``generate_random_name()``. Classes that include it must provide a
    ``self.task`` attribute that references a task dict. Classes that
    use this mixin may set two class variables to alter the behavior
    of ``generate_random_name()``:

    * ``RESOURCE_NAME_FORMAT``: A mktemp(1)-like format string that
      will be used to pattern the generated random string. It must
      contain two separate segments of at least three 'X's; the first
      one will be replaced by a portion of the task ID, and the second
      will be replaced with a random string.
    * ``RESOURCE_NAME_ALLOWED_CHARACTERS``: A string consisting of the
      characters allowed in the random portions of the name.
    """

    RESOURCE_NAME_FORMAT = "rally_XXXXXXXX_XXXXXXXX"
    RESOURCE_NAME_ALLOWED_CHARACTERS = string.ascii_letters + string.digits

    @classmethod
    def _generate_random_part(cls, length):
        """Generate a random string.

        :param length: The length of the random string.
        :returns: string, randomly-generated string of the specified length
                  containing only characters from
                  cls.RESOURCE_NAME_ALLOWED_CHARACTERS
        """
        return "".join(random.choice(cls.RESOURCE_NAME_ALLOWED_CHARACTERS)
                       for i in range(length))

    def generate_random_name(self):
        """Generate pseudo-random resource name for scenarios.

        The name follows a deterministic pattern, which helps support
        out-of-band cleanup of Rally-created resources.

        If possible, a portion of the task ID will be used in the
        random name. If the task ID contains characters that are not
        allowed by the 'RESOURCE_NAME_ALLOWED_CHARACTERS' class
        variable, then a random string, seeded with the task ID, will
        be generated for the task portion of the random name.

        :returns: str, pseudo-random name
        """
        task_id = self.task["uuid"]

        match = _resource_name_placeholder_re.match(self.RESOURCE_NAME_FORMAT)
        if match is None:
            raise ValueError("%s is not a valid resource name format" %
                             self.RESOURCE_NAME_FORMAT)
        parts = match.groupdict()

        result = [parts["prefix"]]

        # NOTE(stpierre): the first part of the random name is a
        # subset of the task ID
        task_id_part = task_id.replace("-", "")[0:len(parts["task"])]

        regen_task_id_part = False
        if len(task_id_part) < len(parts["task"]):
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it is too short. Format: %(format)s" %
                      {"task_id": task_id,
                       "format": self.RESOURCE_NAME_FORMAT})
            regen_task_id_part = True
        elif any(char not in self.RESOURCE_NAME_ALLOWED_CHARACTERS
                 for char in task_id_part):
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it includes disallowed characters. "
                      "Allowed characters: %(chars)s" %
                      {"task_id": task_id,
                       "chars": self.RESOURCE_NAME_ALLOWED_CHARACTERS})
            regen_task_id_part = True
        if regen_task_id_part:
            # NOTE(stpierre): either the task UUID is shorter than the
            # task portion; or the portion of the task ID that we
            # would use contains only characters in
            # resource_name_allowed_characters.
            try:
                # NOTE(stpierre): seed pRNG with task ID so that all random
                # names with the same task ID have the same task ID part
                random.seed(task_id)
                task_id_part = self._generate_random_part(len(parts["task"]))
            finally:
                random.seed()

        result.append(task_id_part)
        result.append(parts["sep"])
        result.append(self._generate_random_part(len(parts["rand"])))
        result.append(parts["suffix"])

        return "".join(result)


def name_matches_pattern(name, fmt, chars):
    """Determine if a resource name matches the given format string.

    Returns True if the name could have been generated by the format
    string, False otherwise.

    :param name: The resource name to check against the format.
    :param fmt: A mktemp(1)-like format string that the string will be
                checked against. It must contain two separate segments
                of at least three 'X's, which have been replaced in
                the resource name by random strings. See the docstring
                for generate_random_name(), above, for more details.
    :param chars: A string consisting of the characters allowed in the
                  random portions of the name.
    :returns: bool
    """
    match = _resource_name_placeholder_re.match(fmt)
    parts = match.groupdict()
    subst = {"prefix": re.escape(parts["prefix"]),
             "sep": re.escape(parts["sep"]),
             "suffix": re.escape(parts["suffix"]),
             "chars": re.escape(chars),
             "task_length": len(parts["task"]),
             "rand_length": len(parts["rand"])}
    name_re = re.compile("%(prefix)s[%(chars)s]{%(task_length)s}%(sep)s"
                         "[%(chars)s]{%(rand_length)s}%(suffix)s$" % subst)
    return name_re.match(name)


def name_matches_object(name, obj):
    """Determine if a resource name could have been created by an object.

    The object should implement RandomNameGeneratorMixin.

    :param name: The resource name to check against the object's
                 RESOURCE_NAME_FORMAT.
    :param obj: The class or object to fetch random name generation
                parameters from.
    :returns: bool
    """
    return name_matches_pattern(name, obj.RESOURCE_NAME_FORMAT,
                                obj.RESOURCE_NAME_ALLOWED_CHARACTERS)


def merge(length, *sources):
    """Merge lists of lists.

    Each source produces (or contains) lists of ordered items.
    Items of each list must be greater or equal to all items of
    the previous list (that implies that items must be comparable).

    The function merges the sources into lists with the length
    equal to given one, except the last list which can be shorter.

    Example:
        it1 = iter([[1, 3, 5], [5, 7, 9, 14], [17, 21, 36, 41]])
        it2 = iter([[2, 2, 4], [9, 10], [16, 19, 23, 26, 91]])
        it3 = iter([[5], [5, 7, 11, 14, 14, 19, 23]])

        it = merge(10, it1, it2, it3)

        for i in it:
            print i

    prints out:
        [1, 2, 2, 3, 4, 5, 5, 5, 5, 7, 7, 9, 9, 10]
        [11, 14, 14, 14, 16, 17, 19, 19, 21, 23, 23]
        [26, 36, 41, 91]

    :param: length, length of generated lists, except the last one.
    :param: sources, generators that produce lists of items to merge
    """

    streams = [
        {"data": [], "gen": src}
        for src in sources]

    out_chunk = []
    while True:
        while len(out_chunk) < length:

            # Least right item among streams
            lri = None

            # Refresh data if needed
            for s in streams:
                if s["gen"] and not s["data"]:
                    try:
                        while not s["data"]:
                            s["data"] = next(s["gen"])
                    except StopIteration:
                        s["gen"] = None

                # ... and define least right item
                if s["data"]:
                    rightmost_item = s["data"][-1]
                    if (lri is None) or (rightmost_item < lri):
                        lri = rightmost_item

            # No more data to merge
            if lri is None:
                break

            to_merge = []
            for s in streams:
                if s["data"]:
                    pos = bisect.bisect_right(s["data"], lri)
                    to_merge.append(s["data"][:pos])
                    s["data"] = s["data"][pos:]

            out_chunk += heapq.merge(*to_merge)

        if out_chunk:
            if len(out_chunk) > length:
                yield out_chunk[:length]
                out_chunk = out_chunk[length:]
            else:
                yield out_chunk
                out_chunk = []
        else:
            return
