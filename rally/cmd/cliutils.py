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

from __future__ import print_function

import os
import sys

from oslo.config import cfg

from rally.openstack.common.apiclient import exceptions
from rally.openstack.common import cliutils
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging
from rally import version

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def pretty_float_formatter(field, ndigits=None):
    """Create a formatter function for the given float field.

    :param field: a float object attribute name to be formatted.
    :param ndigits: The number of digits after decimal point after round.
    If None, then no rounding will be done.
    :returns: the formatter function
    """

    def _formatter(obj):
        value = getattr(obj, field)
        if value is not None:
            if ndigits is not None:
                return round(value, ndigits)
            else:
                return value
        else:
            return "n/a"
    return _formatter


def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault('args', []).insert(0, (args, kwargs))
        return func
    return _decorator


def _methods_of(obj):
    """Get all callable methods of an object that don't start with underscore

    returns a list of tuples of the form (method_name, method)
    """
    result = []
    for i in dir(obj):
        if callable(getattr(obj, i)) and not i.startswith('_'):
            result.append((i, getattr(obj, i)))
    return result


def _add_command_parsers(categories, subparsers):
    parser = subparsers.add_parser('version')

    parser = subparsers.add_parser('bash-completion')
    parser.add_argument('query_category', nargs='?')

    for category in categories:
        command_object = categories[category]()

        parser = subparsers.add_parser(category)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest='action')

        for (action, action_fn) in _methods_of(command_object):
            parser = category_subparsers.add_parser(action)

            action_kwargs = []
            for args, kwargs in getattr(action_fn, 'args', []):
                # FIXME(markmc): hack to assume dest is the arg name without
                # the leading hyphens if no dest is supplied
                kwargs.setdefault('dest', args[0][2:])
                if kwargs['dest'].startswith('action_kwarg_'):
                    action_kwargs.append(kwargs['dest'][len('action_kwarg_'):])
                else:
                    action_kwargs.append(kwargs['dest'])
                    kwargs['dest'] = 'action_kwarg_' + kwargs['dest']

                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=action_fn)
            parser.set_defaults(action_kwargs=action_kwargs)

            parser.add_argument('action_args', nargs='*')


def run(argv, categories):
    parser = lambda subparsers: _add_command_parsers(categories, subparsers)
    category_opt = cfg.SubCommandOpt('category',
                                     title='Command categories',
                                     help='Available categories',
                                     handler=parser)
    CONF.register_cli_opt(category_opt)

    try:
        cfg.CONF(argv[1:], project='rally', version=version.version_string())
        logging.setup("rally")
        if not CONF.get('log_config_append'):
            # The below two lines are to disable noise from request module. The
            # standard way should be we make such lots of settings on the root
            # rally. However current oslo codes doesn't support such interface.
            # So I choose to use a 'hacking' way to avoid INFO logs from
            # request module where user didn't give specific log configuration.
            # And we could remove this hacking after oslo.log has such
            # interface.
            LOG.debug("INFO logs from urllib3 and requests module are hide.")
            requests_log = logging.getLogger("requests").logger
            requests_log.setLevel(logging.logging.WARNING)
            urllib3_log = logging.getLogger("urllib3").logger
            urllib3_log.setLevel(logging.logging.WARNING)
    except cfg.ConfigFilesNotFoundError:
        cfgfile = CONF.config_file[-1] if CONF.config_file else None
        if cfgfile and not os.access(cfgfile, os.R_OK):
            st = os.stat(cfgfile)
            print(_("Could not read %s. Re-running with sudo") % cfgfile)
            try:
                os.execvp('sudo', ['sudo', '-u', '#%s' % st.st_uid] + sys.argv)
            except Exception:
                print(_('sudo failed, continuing as if nothing happened'))

        print(_('Please re-run %s as root.') % argv[0])
        return(2)

    if CONF.category.name == "version":
        print(version.version_string())
        return(0)

    if CONF.category.name == "bash-completion":
        if not CONF.category.query_category:
            print(" ".join(categories.keys()))
        elif CONF.category.query_category in categories:
            fn = categories[CONF.category.query_category]
            command_object = fn()
            actions = _methods_of(command_object)
            print(" ".join([k for (k, v) in actions]))
        return(0)

    fn = CONF.category.action_fn
    fn_args = [arg.decode('utf-8') for arg in CONF.category.action_args]
    fn_kwargs = {}
    for k in CONF.category.action_kwargs:
        v = getattr(CONF.category, 'action_kwarg_' + k)
        if v is None:
            continue
        if isinstance(v, basestring):
            v = v.decode('utf-8')
        fn_kwargs[k] = v

    # call the action with the remaining arguments
    # check arguments
    try:
        cliutils.validate_args(fn, *fn_args, **fn_kwargs)
    except exceptions.MissingArgs as e:
        # NOTE(mikal): this isn't the most helpful error message ever. It is
        # long, and tells you a lot of things you probably don't want to know
        # if you just got a single arg wrong.
        print(fn.__doc__)
        CONF.print_help()
        print(e)
        return(1)
    try:
        ret = fn(*fn_args, **fn_kwargs)
        return(ret)
    except Exception:
        print(_("Command failed, please check log for more info"))
        raise
