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
import collections
import copy
import ctypes
import heapq
import inspect
import multiprocessing
import random
import re
import string
import sys
import time

from six import moves

from rally.common import logging
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
    """Timer based on context manager interface."""

    def __enter__(self):
        self.error = None
        self.start = time.time()
        return self

    def timestamp(self):
        return self.start

    def finish_timestamp(self):
        return self.finish

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
    stored in RAM. Being a true system-level singleton, this allows safely
    share integer among processes and threads.
    """

    def __init__(self, base_value=0):
        self.__int = multiprocessing.Value("I", base_value)

    def __int__(self):
        return self.__int.value

    def __str__(self):
        return str(self.__int.value)

    def __iter__(self):
        return self

    def __next__(self):
        with self.__int._lock:
            value = self.__int.value
            self.__int.value += 1
            if self.__int.value > value:
                return value
            raise StopIteration

    def next(self):
        return self.__next__()

    def reset(self):
        with self.__int._lock:
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
    for i, e in enumerate(lst):
        if predicate(e):
            return i
    return None


@logging.log_deprecated(message="Its not used elsewhere in Rally already.",
                        rally_version="0.4.1")
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


class RandomNameGeneratorMixin(object):
    """Mixin for objects that need to generate random names.

    This mixin provides one method,
    ``generate_random_name()``. Classes that include it must provide a
    ``self.task`` attribute that references a task dict or a
    ``self.verification`` attribute that references a verification dict.
    Classes that use this mixin may set two class variables to alter the
    behavior of ``generate_random_name()``:

    * ``RESOURCE_NAME_FORMAT``: A mktemp(1)-like format string that
      will be used to pattern the generated random string. It must
      contain two separate segments of at least three 'X's; the first
      one will be replaced by a portion of the task ID, and the second
      will be replaced with a random string.
    * ``RESOURCE_NAME_ALLOWED_CHARACTERS``: A string consisting of the
      characters allowed in the random portions of the name.
    """
    _resource_name_placeholder_re = re.compile(
        "^(?P<prefix>.*?)(?P<task>X{3,})(?P<sep>[^X]+?)(?P<rand>X{3,})"
        "(?P<suffix>.*)$")

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

    @classmethod
    def _generate_task_id_part(cls, task_id, length):
        # NOTE(stpierre): the first part of the random name is a
        # subset of the task ID
        task_id_part = task_id.replace("-", "")[0:length]

        if len(task_id_part) < length:
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it is too short. Format: %(format)s" %
                      {"task_id": task_id,
                       "format": cls.RESOURCE_NAME_FORMAT})
        elif any(char not in cls.RESOURCE_NAME_ALLOWED_CHARACTERS
                 for char in task_id_part):
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it includes disallowed characters. "
                      "Allowed characters are: %(chars)s" %
                      {"task_id": task_id,
                       "chars": cls.RESOURCE_NAME_ALLOWED_CHARACTERS})
        else:
            return task_id_part

        # NOTE(stpierre): either the task UUID is shorter than the
        # task portion; or the portion of the task ID that we
        # would use contains only characters in
        # resource_name_allowed_characters.
        try:
            # NOTE(stpierre): seed pRNG with task ID so that all random
            # names with the same task ID have the same task ID part
            random.seed(task_id)
            return cls._generate_random_part(length)
        finally:
            random.seed()

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
        if hasattr(self, "task"):
            task_id = self.task["uuid"]
        elif hasattr(self, "verification"):
            task_id = self.verification["uuid"]

        match = self._resource_name_placeholder_re.match(
            self.RESOURCE_NAME_FORMAT)
        if match is None:
            raise ValueError("%s is not a valid resource name format" %
                             self.RESOURCE_NAME_FORMAT)
        parts = match.groupdict()
        return "".join([
            parts["prefix"],
            self._generate_task_id_part(task_id, len(parts["task"])),
            parts["sep"],
            self._generate_random_part(len(parts["rand"])),
            parts["suffix"]])

    @classmethod
    def name_matches_object(cls, name, task_id=None, exact=True):
        """Determine if a resource name could have been created by this class.

        :param name: The resource name to check against this class's
                     RESOURCE_NAME_FORMAT.
        :param task_id: The task ID that must match the task portion of
                        the random name
        :param exact: If False, then additional information may follow
                      the expected name. (For instance, this is useful
                      when bulk creating instances, since Nova
                      automatically appends a UUID to each instance
                      created thusly.)
        :returns: bool
        """
        match = cls._resource_name_placeholder_re.match(
            cls.RESOURCE_NAME_FORMAT)
        parts = match.groupdict()
        subst = {
            "prefix": re.escape(parts["prefix"]),
            "sep": re.escape(parts["sep"]),
            "suffix": re.escape(parts["suffix"]),
            "chars": re.escape(cls.RESOURCE_NAME_ALLOWED_CHARACTERS),
            "rand_length": len(parts["rand"])}
        if task_id:
            subst["task_id"] = cls._generate_task_id_part(task_id,
                                                          len(parts["task"]))
        else:
            subst["task_id"] = "[%s]{%s}" % (subst["chars"],
                                             len(parts["task"]))
        subst["extra"] = "" if exact else ".*"
        name_re = re.compile(
            "%(prefix)s%(task_id)s%(sep)s"
            "[%(chars)s]{%(rand_length)s}%(suffix)s%(extra)s$" % subst)
        return bool(name_re.match(name))


def name_matches_object(name, *objects, **kwargs):
    """Determine if a resource name could have been created by given objects.

    The object(s) must implement RandomNameGeneratorMixin.

    It will often be more efficient to pass a list of classes to
    name_matches_object() than to perform multiple
    name_matches_object() calls, since this function will deduplicate
    identical name generation options.

    :param name: The resource name to check against the object's
                 RESOURCE_NAME_FORMAT.
    :param *objects: Classes or objects to fetch random name
                     generation parameters from.
    :param **kwargs: Additional keyword args. See the docstring for
                     RandomNameGenerator.name_matches_object() for
                     details on what args are recognized.
    :returns: bool
    """
    unique_rng_options = {}
    for obj in objects:
        key = (obj.RESOURCE_NAME_FORMAT, obj.RESOURCE_NAME_ALLOWED_CHARACTERS)
        if key not in unique_rng_options:
            unique_rng_options[key] = obj
    return any(obj.name_matches_object(name, **kwargs)
               for obj in unique_rng_options.values())


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


def interruptable_sleep(sleep_time, atomic_delay=0.1):
    """Return after sleep_time seconds.

    Divide sleep_time by atomic_delay, and call time.sleep N times.
    This should give a chance to interrupt current thread.

    :param sleep_time: idle time of method (in seconds).
    :param atomic_delay: parameter with which  time.sleep would be called
                         int(sleep_time / atomic_delay) times.
    """
    if atomic_delay <= 0:
        raise ValueError("atomic_delay should be > 0")

    if sleep_time >= 0:
        if sleep_time < 1:
            return time.sleep(sleep_time)

        for x in moves.xrange(int(sleep_time / atomic_delay)):
            time.sleep(atomic_delay)

        left = sleep_time - (int(sleep_time / atomic_delay)) * atomic_delay
        if left:
            time.sleep(left)
    else:
        raise ValueError("sleep_time should be >= 0")


def terminate_thread(thread_ident, exc_type=exceptions.ThreadTimeoutException):
    """Terminate a python thread.

    Use PyThreadState_SetAsyncExc to terminate thread.

    :param thread_ident: threading.Thread.ident value
    :param exc_type: an Exception type to be raised
    """

    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread_ident), ctypes.py_object(exc_type))


def timeout_thread(queue):
    """Terminate threads by timeout.

    Function need to be run in separate thread. Its designed to terminate
    threads which are running longer then timeout.

    Parent thread will put tuples (thread_ident, deadline) in the queue,
    where `thread_ident` is Thread.ident value of thread to watch, and
    `deadline` is timestamp when thread should be terminated. Also tuple
    (None, None) should be put when all threads are exited and no more
    threads to watch.

    :param queue: Queue object to communicate with parent thread.
    """

    all_threads = collections.deque()
    while True:
        if not all_threads:
            timeout = None
        else:
            thread, deadline = all_threads[0]
            timeout = deadline - time.time()
        try:
            next_thread = queue.get(timeout=timeout)
            all_threads.append(next_thread)
        except (moves.queue.Empty, ValueError):
            # NOTE(rvasilets) Empty means that timeout was occurred.
            # ValueError means that timeout lower than 0.
            if thread.isAlive():
                LOG.info("Thread %s is timed out. Terminating." % thread.ident)
                terminate_thread(thread.ident)
            all_threads.popleft()

        if next_thread == (None, None,):
            return


class LockedDict(dict):
    """This represents dict which can be locked for updates.

    It is read-only by default, but it can be updated via context manager
    interface:

    d = LockedDict(foo="bar")
    d["spam"] = 42  # RuntimeError
    with d.unlocked():
         d["spam"] = 42  # Works
    """

    def __init__(self, *args, **kwargs):
        super(LockedDict, self).__init__(*args, **kwargs)
        self._is_locked = True
        self._is_ready_to_be_unlocked = False

        def lock(obj):
            if isinstance(obj, dict):
                return LockedDict(obj)
            elif isinstance(obj, list):
                return tuple([lock(v) for v in obj])
            return obj

        with self.unlocked():
            for k, v in self.items():
                self[k] = lock(v)

    def _check_is_unlocked(self):
        if self._is_locked:
            raise RuntimeError("Trying to change read-only dict %r" % self)

    def unlocked(self):
        self._is_ready_to_be_unlocked = True
        return self

    def __deepcopy__(self, memo=None):
        def unlock(obj):
            if isinstance(obj, LockedDict):
                obj = dict(obj)
                for k, v in obj.items():
                    obj[k] = unlock(v)
            elif type(obj) == tuple:
                obj = tuple([unlock(v) for v in obj])
            return obj
        return copy.deepcopy(unlock(self), memo=memo)

    def __enter__(self, *args):
        if self._is_ready_to_be_unlocked:
            self._is_locked = False

    def __exit__(self, *args):
        self._is_ready_to_be_unlocked = False
        self._is_locked = True

    def __setitem__(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).__setitem__(*args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).__delitem__(*args, **kwargs)

    def pop(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).pop(*args, **kwargs)

    def popitem(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).popitem(*args, **kwargs)

    def update(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).update(*args, **kwargs)

    def setdefault(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).setdefault(*args, **kwargs)

    def clear(self, *args, **kwargs):
        self._check_is_unlocked()
        return super(LockedDict, self).clear(*args, **kwargs)


def format_float_to_str(num):
    """Format number into human-readable float format.

     More precise it convert float into the string and remove redundant
     zeros from the floating part.
     It will format the number by the following examples:
     0.0000001 -> 0.0
     0.000000 -> 0.0
     37 -> 37.0
     1.0000001 -> 1.0
     1.0000011 -> 1.000001
     1.0000019 -> 1.000002

    :param num: Number to be formatted
    :return: string representation of the number
    """

    num_str = "%f" % num
    float_part = num_str.split(".")[1].rstrip("0") or "0"
    return num_str.split(".")[0] + "." + float_part


class DequeAsQueue(object):
    """Allows to use some of Queue methods on collections.deque."""

    def __init__(self, deque):
        self.deque = deque

    def qsize(self):
        return len(self.deque)

    def put(self, value):
        self.deque.append(value)

    def get(self):
        return self.deque.popleft()

    def empty(self):
        return bool(self.deque)


class Stopwatch(object):
    """Allows to sleep till specified time since start."""

    def __init__(self, stop_event=None):
        """Creates Stopwatch.

        :param stop_event: optional threading.Event to use for waiting
            allows to interrupt sleep. If not provided time.sleep
            will be used instead.
        """
        self._stop_event = stop_event

    def start(self):
        self._start_time = time.time()

    def sleep(self, sec):
        """Sleeps till specified second since start."""
        target_time = self._start_time + sec
        current_time = time.time()
        if current_time >= target_time:
            return
        time_to_sleep = target_time - current_time
        self._sleep(time_to_sleep)

    def _sleep(self, sec):
        if self._stop_event:
            self._stop_event.wait(sec)
        else:
            interruptable_sleep(sec)
