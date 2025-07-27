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

from __future__ import annotations

import bisect
import collections
import copy
import ctypes
import heapq
import inspect
import io
import multiprocessing
import os
import queue as queue_m
import random
import re
import shutil
import string
import sys
import tempfile
import time
import typing as t
import uuid

from rally.common.io import junit
from rally.common import logging
from rally import exceptions

if t.TYPE_CHECKING:  # pragma: no cover
    import threading


LOG = logging.getLogger(__name__)


class ImmutableMixin:
    _inited = False

    def __init__(self) -> None:
        self._inited = True

    def __setattr__(self, key: str, value: t.Any) -> None:
        if self._inited:
            raise AttributeError("This object is immutable.")
        super(ImmutableMixin, self).__setattr__(key, value)


class EnumMixin:
    def __iter__(self) -> t.Iterator[t.Any]:
        for k, v in map(lambda x: (x, getattr(self, x)), dir(self)):
            if not k.startswith("_"):
                yield v


class StdOutCapture:
    def __init__(self) -> None:
        self.stdout = sys.stdout

    def __enter__(self) -> io.StringIO:
        sys.stdout = io.StringIO()
        return sys.stdout

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: t.Any,
    ) -> None:
        sys.stdout = self.stdout


class StdErrCapture:
    def __init__(self) -> None:
        self.stderr = sys.stderr

    def __enter__(self) -> io.StringIO:
        sys.stderr = io.StringIO()
        return sys.stderr

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        traceback: t.Any,
    ) -> None:
        sys.stderr = self.stderr


class Timer:
    """Timer based on context manager interface."""

    def __enter__(self) -> Timer:
        self.error: (
            tuple[type[BaseException], BaseException, t.Any] | None
        ) = None
        self.start = time.time()
        return self

    def timestamp(self) -> float:
        return self.start

    def finish_timestamp(self) -> float:
        return self.finish

    def __exit__(
        self,
        type: type[BaseException] | None,
        value: BaseException | None,
        tb: t.Any,
    ) -> None:
        self.finish = time.time()
        if type and value:
            self.error = (type, value, tb)

    @t.overload
    def duration(self, fmt: t.Literal[False] = False) -> float:
        ...

    @t.overload
    def duration(self, fmt: t.Literal[True]) -> str:
        ...

    def duration(self, fmt: bool = False) -> float | str:
        duration = self.finish - self.start
        if not fmt:
            return duration
        if duration > 60:
            return "%.2f min" % (duration / 60)
        if duration > 0.1:
            return "%.2f sec" % duration
        return "%.2f msec" % (duration * 1000)


class Struct:
    def __init__(self, **entries: t.Any) -> None:
        self.__dict__.update(entries)

    def __getitem__(self, item: str, default: t.Any = None) -> t.Any:
        return getattr(self, item, default)


class RAMInt:
    """Share RAM integer, for IPC.

    This class represents iterable which refers directly to an integer value
    stored in RAM. Being a true system-level singleton, this allows safely
    share integer among processes and threads.
    """

    def __init__(self, base_value: int = 0) -> None:
        self.__int = multiprocessing.Value("I", base_value)

    def __int__(self) -> int:
        return self.__int.value

    def __str__(self) -> str:
        return str(self.__int.value)

    def __iter__(self) -> RAMInt:
        return self

    def __next__(self) -> int:
        with self.__int._lock:  # type: ignore[attr-defined]
            value = self.__int.value
            self.__int.value += 1
            if self.__int.value > value:
                return value
            raise StopIteration

    def next(self) -> int:
        return self.__next__()

    def reset(self) -> None:
        with self.__int._lock:  # type: ignore[attr-defined]
            self.__int.value = 0


@logging.log_deprecated("it was an inner helper.", rally_version="3.0.0")
def get_method_class(func: t.Any) -> type | None:
    """Return the class that defined the given method.

    :param func: function to get the class for.
    :returns: class object or None if func is not an instance method.
    """
    if hasattr(func, "im_class"):
        # this check works in Python 2
        for cls in inspect.getmro(func.im_class):  # type: ignore[attr-defined]
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


@logging.log_deprecated("it was an inner helper.", rally_version="3.0.0")
def first_index(
    lst: list[t.Any],
    predicate: t.Callable[[t.Any], bool],
) -> int | None:
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


def retry(
    times: int,
    func: t.Callable[..., t.Any],
    *args: t.Any,
    **kwargs: t.Any,
) -> t.Any:
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


@logging.log_deprecated("it is openstack specific.", rally_version="3.0.0")
def iterate_per_tenants(
    users: list[dict[str, t.Any]],
) -> t.Iterator[tuple[dict[str, t.Any], str]]:
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
    def _get_resource_name_format(cls) -> str:
        return cls.RESOURCE_NAME_FORMAT

    @classmethod
    def _get_resource_name_allowed_characters(cls) -> str:
        return cls.RESOURCE_NAME_ALLOWED_CHARACTERS

    @classmethod
    def _generate_random_part(cls, length: int) -> str:
        """Generate a random string.

        :param length: The length of the random string.
        :returns: string, randomly-generated string of the specified length
                  containing only characters from
                  cls.RESOURCE_NAME_ALLOWED_CHARACTERS
        """
        return "".join(
            random.choice(cls._get_resource_name_allowed_characters())
            for i in range(length))

    @classmethod
    def _generate_task_id_part(cls, task_id: str, length: int) -> str:
        # NOTE(stpierre): the first part of the random name is a
        # subset of the task ID
        task_id_part = task_id.replace("-", "")[0:length]

        if len(task_id_part) < length:
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it is too short. Format: %(format)s"
                      % {"task_id": task_id,
                         "format": cls._get_resource_name_format()})
        elif any(char not in cls._get_resource_name_allowed_characters()
                 for char in task_id_part):
            LOG.debug("Task ID %(task_id)s cannot be included in a random "
                      "name because it includes disallowed characters. "
                      "Allowed characters are: %(chars)s"
                      % {"task_id": task_id,
                         "chars": cls._get_resource_name_allowed_characters()})
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

    def get_owner_id(self) -> str | None:
        if hasattr(self, "task"):
            return self.task["uuid"]
        elif hasattr(self, "verification"):
            return self.verification["uuid"]

    def generate_random_name(self) -> str:
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
        task_id = self.get_owner_id()

        match = self._resource_name_placeholder_re.match(
            self._get_resource_name_format())
        if match is None:
            raise ValueError("%s is not a valid resource name format" %
                             self._get_resource_name_format())
        parts = match.groupdict()
        return "".join([
            parts["prefix"],
            self._generate_task_id_part(task_id or "", len(parts["task"])),
            parts["sep"],
            self._generate_random_part(len(parts["rand"])),
            parts["suffix"]])

    @classmethod
    def name_matches_object(
        cls,
        name: str,
        task_id: str | None = None,
        exact: bool = True,
    ) -> bool:
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
            cls._get_resource_name_format())
        if match is None:
            raise ValueError("%s is not a valid resource name format" %
                             cls._get_resource_name_format())
        parts = match.groupdict()
        subst = {
            "prefix": re.escape(parts["prefix"]),
            "sep": re.escape(parts["sep"]),
            "suffix": re.escape(parts["suffix"]),
            "chars": re.escape(cls._get_resource_name_allowed_characters()),
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


def name_matches_object(name: str, *objects: t.Any, **kwargs: t.Any) -> bool:
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
        key = (obj._get_resource_name_format(),
               obj._get_resource_name_allowed_characters())
        if key not in unique_rng_options:
            unique_rng_options[key] = obj
    return any(obj.name_matches_object(name, **kwargs)
               for obj in unique_rng_options.values())


def make_name_matcher(*names: str) -> type[RandomNameGeneratorMixin]:
    """Construct a matcher for custom names

    In case of contexts, there can be custom names. To reuse common cleanup
    mechanism for cleaning up such resources, this method creates a subclass of
    RandomNameGeneratorMixin with customized `name_matches_object` method.
    """
    class CustomNameMatcher(RandomNameGeneratorMixin):
        # generate unique string to guarantee processing that custom names
        RESOURCE_NAME_FORMAT = str(uuid.uuid4())

        NAMES = names

        @classmethod
        def name_matches_object(
            cls,
            name: str,
            task_id: str | None = None,
            exact: bool = True,
        ) -> bool:
            return name in cls.NAMES

    return CustomNameMatcher


@logging.log_deprecated("it was an inner helper.", rally_version="3.0.0")
def merge(length: int, *sources: t.Any) -> t.Any:
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

    out_chunk: list[t.Any] = []
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


def interruptable_sleep(sleep_time: float, atomic_delay: float = 0.1) -> None:
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

        for x in range(int(sleep_time / atomic_delay)):
            time.sleep(atomic_delay)

        left = sleep_time - (int(sleep_time / atomic_delay)) * atomic_delay
        if left:
            time.sleep(left)
    else:
        raise ValueError("sleep_time should be >= 0")


def terminate_thread(
    thread_ident: int,
    exc_type: type[BaseException] = exceptions.ThreadTimeoutException,
) -> None:
    """Terminate a python thread.

    Use PyThreadState_SetAsyncExc to terminate thread.

    :param thread_ident: threading.Thread.ident value
    :param exc_type: an Exception type to be raised
    """

    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread_ident), ctypes.py_object(exc_type))


def timeout_thread(
    queue: queue_m.Queue[tuple[threading.Thread, float] | tuple[None, None]],
) -> None:
    """Terminate threads by timeout.

    Function need to be run in separate thread. Its designed to terminate
    threads which are running longer then timeout.

    Parent thread will put tuples (thread, deadline) in the queue,
    where `thread` is the threading.Thread object to watch, and
    `deadline` is timestamp when thread should be terminated. Also tuple
    (None, None) should be put when all threads are exited and no more
    threads to watch.

    :param queue: Queue object to communicate with parent thread.
    """

    all_threads: collections.deque[
        tuple[threading.Thread, float] | tuple[None, None]
    ] = collections.deque()
    thread = None
    while True:
        if not all_threads:
            timeout = None
        else:
            thread, deadline = all_threads[0]
            if thread is None or deadline is None:
                return
            timeout = deadline - time.time()
        try:
            next_thread = queue.get(timeout=timeout)
            all_threads.append(next_thread)
        except (queue_m.Empty, ValueError):
            # NOTE(rvasilets) Empty means that timeout was occurred.
            # ValueError means that timeout lower than 0.
            if thread and thread.is_alive() and thread.ident is not None:
                LOG.info(f"Thread {thread.ident} is timed out. Terminating.")
                terminate_thread(thread.ident)
            all_threads.popleft()

        if next_thread == (None, None):
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

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super(LockedDict, self).__init__(*args, **kwargs)
        self._is_locked = True
        self._is_ready_to_be_unlocked = False

        def lock(obj: t.Any) -> t.Any:
            if isinstance(obj, dict):
                return LockedDict(obj)
            elif isinstance(obj, list):
                return tuple([lock(v) for v in obj])
            return obj

        with self.unlocked():
            for k, v in self.items():
                self[k] = lock(v)

    def _check_is_unlocked(self) -> None:
        if self._is_locked:
            raise RuntimeError("Trying to change read-only dict %r" % self)

    def unlocked(self) -> LockedDict:
        self._is_ready_to_be_unlocked = True
        return self

    def __deepcopy__(self, memo: t.Any = None) -> LockedDict:
        def unlock(obj: t.Any) -> t.Any:
            if isinstance(obj, LockedDict):
                obj = dict(obj)
                for k, v in obj.items():
                    obj[k] = unlock(v)
            elif isinstance(obj, tuple):
                obj = tuple([unlock(v) for v in obj])
            return obj
        return copy.deepcopy(unlock(self), memo=memo)

    def __enter__(self, *args: t.Any) -> None:
        if self._is_ready_to_be_unlocked:
            self._is_locked = False

    def __exit__(self, *args: t.Any) -> None:
        self._is_ready_to_be_unlocked = False
        self._is_locked = True

    def __setitem__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._check_is_unlocked()
        return super(LockedDict, self).__setitem__(*args, **kwargs)

    def __delitem__(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._check_is_unlocked()
        return super(LockedDict, self).__delitem__(*args, **kwargs)

    def pop(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        self._check_is_unlocked()
        return super(LockedDict, self).pop(*args, **kwargs)

    def popitem(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        self._check_is_unlocked()
        return super(LockedDict, self).popitem(*args, **kwargs)

    def update(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._check_is_unlocked()
        return super(LockedDict, self).update(*args, **kwargs)

    def setdefault(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        self._check_is_unlocked()
        return super(LockedDict, self).setdefault(*args, **kwargs)

    def clear(self, *args: t.Any, **kwargs: t.Any) -> None:
        self._check_is_unlocked()
        return super(LockedDict, self).clear(*args, **kwargs)


class DequeAsQueue(object):
    """Allows to use some of Queue methods on collections.deque."""

    def __init__(self, deque: collections.deque) -> None:
        self.deque = deque

    def qsize(self) -> int:
        return len(self.deque)

    def put(self, value: t.Any) -> None:
        self.deque.append(value)

    def get(self) -> t.Any:
        return self.deque.popleft()

    def empty(self) -> bool:
        return bool(self.deque)


class Stopwatch(object):
    """Allows to sleep till specified time since start."""

    def __init__(self, stop_event: threading.Event | None = None) -> None:
        """Creates Stopwatch.

        :param stop_event: optional threading.Event to use for waiting
            allows to interrupt sleep. If not provided time.sleep
            will be used instead.
        """
        self._stop_event = stop_event

    def start(self) -> None:
        self._start_time = time.time()

    def sleep(self, sec: float) -> None:
        """Sleeps till specified second since start."""
        target_time = self._start_time + sec
        current_time = time.time()
        if current_time >= target_time:
            return
        time_to_sleep = target_time - current_time
        self._sleep(time_to_sleep)

    def _sleep(self, sec: float) -> None:
        if self._stop_event:
            self._stop_event.wait(sec)
        else:
            interruptable_sleep(sec)


def generate_random_path(root_dir: str | None = None) -> str:
    """Generates a vacant name for a file or dir at the specified place.

    :param root_dir: Name of a directory to generate path in. If None (default
        behaviour), temporary directory (i.e /tmp in linux) will be used.
    """
    root_dir = root_dir or tempfile.gettempdir()
    path = None
    while path is None:
        candidate = os.path.join(root_dir, str(uuid.uuid4()))
        if not os.path.exists(candidate):
            path = candidate
    return path


class BackupHelper(object):
    def __init__(self) -> None:
        self._tempdir = generate_random_path()

        os.mkdir(self._tempdir)

        self._stored_data: dict[str, str] = {}
        self._rollback_actions: list[
            tuple[t.Callable[..., t.Any], tuple[t.Any, ...], dict[str, t.Any]]
        ] = []

    def backup(self, original_path: str) -> None:
        if original_path in self._stored_data:
            raise exceptions.RallyException(
                "Failed to back up %s since it was already stored."
                % original_path)
        backup_path = generate_random_path(self._tempdir)
        LOG.debug("Creating backup of %s in %s" % (original_path, backup_path))
        try:
            shutil.copytree(original_path, backup_path, symlinks=True)
        except Exception:
            # Ooops. something went wrong
            self.rollback()
            raise
        self._stored_data[original_path] = backup_path

    def rollback(self) -> None:
        LOG.debug("Performing rollback of stored data.")
        for original_path, stored_path in self._stored_data.copy().items():
            if os.path.exists(original_path):
                shutil.rmtree(original_path)
            shutil.copytree(stored_path, original_path, symlinks=True)
            # not to delete the same path in __del__ method
            self._stored_data.pop(original_path)

        for m, args, kwargs in self._rollback_actions:
            m(*args, **kwargs)

    def add_rollback_action(
        self,
        method: t.Callable[..., t.Any],
        *args: t.Any,
        **kwargs: t.Any,
    ) -> None:
        self._rollback_actions.append((method, args, kwargs))

    def __enter__(self) -> BackupHelper:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: t.Any,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def __call__(self, path: str) -> BackupHelper:
        self.backup(path)
        return self

    def __del__(self) -> None:
        for path in self._stored_data.values():
            if os.path.exists(path):
                LOG.debug("Deleting %s" % path)
                shutil.rmtree(path)


@logging.log_deprecated("it was an inner helper.", rally_version="3.0.0")
def prettify_xml(elem: t.Any, level: int = 0) -> None:
    junit._prettify_xml(elem, level=level)
