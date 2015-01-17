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

import argparse
import inspect
import os
import sys

import jsonschema
from oslo_config import cfg
import six

from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils
from rally.common import version
from rally import exceptions
from rally.openstack.common import cliutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


# Some CLI-specific constants
MARGIN = 3


def make_header(text, size=80, symbol="-"):
    """Unified way to make header message to CLI.

    :param text: what text to write
    :param size: Length of header decorative line
    :param symbol: What symbol to use to create header
    """
    header = symbol * size + "\n"
    header += " %s\n" % text
    header += symbol * size + "\n"
    return header


class CategoryParser(argparse.ArgumentParser):

    """Customized arguments parser

    We need this one to override hardcoded behavior.
    So, we want to print item's help instead of 'error: too few arguments'.
    Also, we want not to print positional arguments in help messge.
    """

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        formatter.add_usage(self.usage, self._actions,
                            self._mutually_exclusive_groups)

        # description
        formatter.add_text(self.description)

        # positionals, optionals and user-defined groups
        # INFO(oanufriev) _action_groups[0] contains positional arguments.
        for action_group in self._action_groups[1:]:
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()

    def error(self, message):
        self.print_help(sys.stderr)
        sys.exit(2)


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


def deprecated_args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        func.__dict__.setdefault("deprecated_args", [])
        func.deprecated_args.append(args[0])
        if "help" in kwargs.keys():
            warn_message = "DEPRECATED!"
            kwargs["help"] = " ".join([warn_message, kwargs["help"]])
        return func
    return _decorator


def _methods_of(cls):
    """Get all callable methods of a class that don't start with underscore.

    :returns: a list of tuples of the form (method_name, method)
    """
    methods = [m for m in inspect.getmembers(cls, predicate=inspect.ismethod)
               if not m[0].startswith('_')]
    return methods


def _compose_category_description(category):

    descr_pairs = _methods_of(category)

    description = ""
    doc = category.__doc__
    if doc:
        description = doc.strip()
    if descr_pairs:
        description += "\n\nCommands:\n"
        sublen = lambda item: len(item[0])
        first_column_len = max(map(sublen, descr_pairs)) + MARGIN
        for item in descr_pairs:
            name = item[0]
            if item[1].__doc__:
                doc = utils.parse_docstring(
                    item[1].__doc__)["short_description"]
            else:
                doc = ""
            name += " " * (first_column_len - len(name))
            description += "   %s%s\n" % (name, doc)

    return description


def _compose_action_description(action_fn):
    description = ""
    if action_fn.__doc__:
        parsed_doc = utils.parse_docstring(action_fn.__doc__)
        short = parsed_doc.get("short_description")
        long = parsed_doc.get("long_description")

        description = "%s\n\n%s" % (short, long) if long else short

    return description


def _add_command_parsers(categories, subparsers):

    # INFO(oanufriev) This monkey patching makes our custom parser class to be
    # used instead of native.  This affects all subparsers down from
    # 'subparsers' parameter of this function (categories and actions).
    subparsers._parser_class = CategoryParser

    parser = subparsers.add_parser('version')

    parser = subparsers.add_parser('bash-completion')
    parser.add_argument('query_category', nargs='?')

    for category in categories:
        command_object = categories[category]()
        descr = _compose_category_description(categories[category])
        parser = subparsers.add_parser(
            category, description=descr,
            formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest='action')

        for action, action_fn in _methods_of(command_object):
            descr = _compose_action_description(action_fn)
            parser = category_subparsers.add_parser(
                action,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=descr, help=descr)

            action_kwargs = []
            for args, kwargs in getattr(action_fn, 'args', []):
                # FIXME(markmc): hack to assume dest is the arg name without
                # the leading hyphens if no dest is supplied
                kwargs.setdefault('dest', args[0][2:])
                action_kwargs.append(kwargs['dest'])
                kwargs['dest'] = 'action_kwarg_' + kwargs['dest']
                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=action_fn)
            parser.set_defaults(action_kwargs=action_kwargs)
            parser.add_argument('action_args', nargs='*')


def validate_deprecated_args(argv, fn):
    if (len(argv) > 3
       and (argv[2] == fn.func_name)
       and getattr(fn, "deprecated_args", None)):
        for item in fn.deprecated_args:
            if item in argv[3:]:
                LOG.warning("Deprecated argument %s for %s." % (item,
                                                                fn.func_name))


def run(argv, categories):
    parser = lambda subparsers: _add_command_parsers(categories, subparsers)
    category_opt = cfg.SubCommandOpt('category',
                                     title='Command categories',
                                     help='Available categories',
                                     handler=parser)

    CONF.register_cli_opt(category_opt)

    try:
        CONF(argv[1:], project='rally', version=version.version_string())
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
            requests_log.setLevel(logging.WARNING)
            urllib3_log = logging.getLogger("urllib3").logger
            urllib3_log.setLevel(logging.WARNING)
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
        print(_generate_bash_completion_script())
        return(0)

    fn = CONF.category.action_fn
    fn_args = [arg.decode('utf-8') for arg in CONF.category.action_args]
    fn_kwargs = {}
    for k in CONF.category.action_kwargs:
        v = getattr(CONF.category, 'action_kwarg_' + k)
        if v is None:
            continue
        if isinstance(v, six.string_types):
            v = v.decode('utf-8')
        fn_kwargs[k] = v

    # call the action with the remaining arguments
    # check arguments
    try:
        cliutils.validate_args(fn, *fn_args, **fn_kwargs)
    except cliutils.MissingArgs as e:
        # NOTE(mikal): this isn't the most helpful error message ever. It is
        # long, and tells you a lot of things you probably don't want to know
        # if you just got a single arg wrong.
        print(fn.__doc__)
        CONF.print_help()
        print("Missing arguments:")
        for missing in e.missing:
            for arg in fn.args:
                if arg[1].get('dest', '').endswith(missing):
                    print(" " + arg[0][0])
                    break
        return(1)

    try:
        utils.load_plugins("/opt/rally/plugins/")
        utils.load_plugins(os.path.expanduser("~/.rally/plugins/"))

        validate_deprecated_args(argv, fn)
        ret = fn(*fn_args, **fn_kwargs)
        return(ret)
    except (IOError, TypeError, ValueError, exceptions.DeploymentNotFound,
            exceptions.TaskNotFound, jsonschema.ValidationError) as e:
        if logging.is_debug():
            LOG.exception(e)
        print(e)
        return 1
    except Exception:
        print(_("Command failed, please check log for more info"))
        raise


def _generate_bash_completion_script():
    from rally.cmd import main
    bash_data = """
#!/bin/bash

_rally()
{
    declare -A SUBCOMMANDS
    declare -A OPTS

%(data)s

    for OPT in ${!OPTS[*]} ; do
        CMDSUB=(${OPT//_/ })
        SUBCOMMANDS[${CMDSUB[0]}]+="${CMDSUB[1]} "
    done

    COMMANDS="${!SUBCOMMANDS[*]}"
    COMPREPLY=()

    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ $cur =~ (\.|\~|\/).* ]] ; then
        _filedir
    elif [ $COMP_CWORD == "1" ] ; then
        COMPREPLY=($(compgen -W "$COMMANDS" -- ${cur}))
    elif [ $COMP_CWORD == "2" ] ; then
        COMPREPLY=($(compgen -W "${SUBCOMMANDS[${prev}]}" -- ${cur}))
    else
        if [ $prev == "--filename" ] ; then
            _filedir '@(json|ya?ml)'
        elif [ $prev == "--output-file" ] || [ $prev == "--out" ]; then
            _filedir
        else
            COMMAND="${COMP_WORDS[1]}_${COMP_WORDS[2]}"
            COMPREPLY=($(compgen -W "${OPTS[$COMMAND]}" -- ${cur}))
        fi
    fi
    return 0
}
complete -F _rally rally
"""
    completion = ""
    for category, cmds in main.categories.items():
        for name, command in _methods_of(cmds):
            args_list = list()
            for arg in getattr(command, "args", []):
                if getattr(command, "deprecated_args", []):
                    if arg[0][0] not in command.deprecated_args:
                        args_list.append(arg[0][0])
                else:
                    args_list.append(arg[0][0])
            args = " ".join(args_list)

            completion += """    OPTS["{cat}_{cmd}"]="{args}"\n""".format(
                    cat=category, cmd=name, args=args)
    return bash_data % {"data": completion}
