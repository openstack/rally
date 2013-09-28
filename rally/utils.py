# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import itertools
import os
import StringIO
import sys

from rally import exceptions
from rally.openstack.common.gettextutils import _   # noqa
from rally.openstack.common import importutils


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
    for filename in os.listdir(path):
        if filename.startswith('__') or not filename.endswith('.py'):
            continue
        module_name = '%s.%s' % (package, filename[:-3])
        try_append_module(module_name, sys.modules)
