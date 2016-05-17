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
import warnings

import decorator
import jsonschema
from oslo_config import cfg
from oslo_utils import encodeutils
import prettytable
from requests.packages import urllib3
import six
import sqlalchemy.exc

from rally.common.i18n import _
from rally.common import logging
from rally.common.plugin import discover
from rally.common.plugin import info
from rally.common import version
from rally import exceptions


CONFIG_SEARCH_PATHS = [sys.prefix + "/etc/rally", "~/.rally", "/etc/rally"]


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


# Some CLI-specific constants
MARGIN = 3


def find_config_files(path_list):
    for path in path_list:
        abspath = os.path.abspath(os.path.expanduser(path))
        confname = abspath + "/rally.conf"
        if os.path.isfile(confname):
            return [confname]

    return None


class MissingArgs(Exception):
    """Supplied arguments are not sufficient for calling a function."""
    def __init__(self, missing):
        self.missing = missing
        msg = _("Missing arguments: %s") % ", ".join(missing)
        super(MissingArgs, self).__init__(msg)


def validate_args(fn, *args, **kwargs):
    """Check that the supplied args are sufficient for calling a function.

    >>> validate_args(lambda a: None)
    Traceback (most recent call last):
        ...
    MissingArgs: Missing argument(s): a
    >>> validate_args(lambda a, b, c, d: None, 0, c=1)
    Traceback (most recent call last):
        ...
    MissingArgs: Missing argument(s): b, d

    :param fn: the function to check
    :param args: the positional arguments supplied
    :param kwargs: the keyword arguments supplied
    """
    argspec = inspect.getargspec(fn)

    num_defaults = len(argspec.defaults or [])
    required_args = argspec.args[:len(argspec.args) - num_defaults]

    if getattr(fn, "__self__", None):
        required_args.pop(0)

    missing_required_args = required_args[len(args):]
    missing = [arg for arg in missing_required_args if arg not in kwargs]
    if missing:
        raise MissingArgs(missing)


def print_list(objs, fields, formatters=None, sortby_index=0,
               mixed_case_fields=None, field_labels=None,
               normalize_field_names=False,
               table_label=None, print_header=True, print_border=True,
               out=sys.stdout):
    """Print a list or objects as a table, one row per object.

    :param objs: iterable of :class:`Resource`
    :param fields: attributes that correspond to columns, in order
    :param formatters: `dict` of callables for field formatting
    :param sortby_index: index of the field for sorting table rows
    :param mixed_case_fields: fields corresponding to object attributes that
        have mixed case names (e.g., 'serverId')
    :param field_labels: Labels to use in the heading of the table, default to
        fields.
    :param normalize_field_names: If True, field names will be transformed,
        e.g. "Field Name" -> "field_name", otherwise they will be used
        unchanged.
    :param table_label: Label to use as header for the whole table.
    :param print_header: print table header.
    :param print_border: print table border.
    :param out: stream to write output to.

    """
    formatters = formatters or {}
    mixed_case_fields = mixed_case_fields or []
    field_labels = field_labels or fields
    if len(field_labels) != len(fields):
        raise ValueError(_("Field labels list %(labels)s has different number "
                           "of elements than fields list %(fields)s"),
                         {"labels": field_labels, "fields": fields})

    if sortby_index is None:
        kwargs = {}
    else:
        kwargs = {"sortby": field_labels[sortby_index]}
    pt = prettytable.PrettyTable(field_labels)
    pt.align = "l"

    for o in objs:
        row = []
        for field in fields:
            if field in formatters:
                row.append(formatters[field](o))
            else:
                if normalize_field_names:
                    if field in mixed_case_fields:
                        field_name = field.replace(" ", "_")
                    else:
                        field_name = field.lower().replace(" ", "_")
                else:
                    field_name = field

                if isinstance(o, dict):
                    data = o.get(field_name, "")
                else:
                    data = getattr(o, field_name, "")

                row.append(data)
        pt.add_row(row)

    if not print_border or not print_header:
        pt.set_style(prettytable.PLAIN_COLUMNS)
        pt.left_padding_width = 0
        pt.right_padding_width = 1

    table_body = pt.get_string(header=print_header,
                               border=print_border,
                               **kwargs) + "\n"

    table_header = ""

    if table_label:
        table_width = table_body.index("\n")
        table_header = make_table_header(table_label, table_width)
        table_header += "\n"

    if six.PY3:
        if table_header:
            out.write(encodeutils.safe_encode(table_header).decode())
        out.write(encodeutils.safe_encode(table_body).decode())
    else:
        if table_header:
            out.write(encodeutils.safe_encode(table_header))
        out.write(encodeutils.safe_encode(table_body))


def make_table_header(table_label, table_width,
                      junction_char="+", horizontal_char="-",
                      vertical_char="|"):
    """Generalized way make a table header string.

    :param table_label: label to print on header
    :param table_width: total width of table
    :param junction_char: character used where vertical and
        horizontal lines meet.
    :param horizontal_char: character used for horizontal lines.
    :param vertical_char: character used for vertical lines.

    :returns: string
    """

    if len(table_label) >= (table_width - 2):
        raise ValueError(_("Table header %s is longer than total"
                           "width of the table."))

    label_and_space_width = table_width - len(table_label) - 2
    padding = 0 if label_and_space_width % 2 == 0 else 1

    half_table_width = label_and_space_width // 2
    left_spacing = (" " * half_table_width)
    right_spacing = (" " * (half_table_width + padding))

    border_line = "".join((junction_char,
                           (horizontal_char * (table_width - 2)),
                           junction_char,))

    label_line = "".join((vertical_char,
                          left_spacing,
                          table_label,
                          right_spacing,
                          vertical_char,))

    return "\n".join((border_line, label_line,))


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


def suppress_warnings(f):
    f._suppress_warnings = True
    return f


@decorator.decorator
def process_keystone_exc(f, *args, **kwargs):
    from keystoneclient import exceptions as keystone_exc

    try:
        return f(*args, **kwargs)
    except keystone_exc.Unauthorized as e:
        print(_("User credentials are wrong! \n%s") % e)
        return 1
    except keystone_exc.AuthorizationFailure as e:
        print(_("Failed to authorize! \n%s") % e)
        return 1
    except keystone_exc.ConnectionRefused as e:
        print(_("Rally can't reach the Keystone service! \n%s") % e)
        return 1


class CategoryParser(argparse.ArgumentParser):

    """Customized arguments parser

    We need this one to override hardcoded behavior.
    So, we want to print item's help instead of 'error: too few arguments'.
    Also, we want not to print positional arguments in help message.
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
        if message.startswith("argument") and message.endswith("is required"):
            # NOTE(pirsriva) Argparse will currently raise an error
            # message for only 1 missing argument at a time i.e. in the
            # error message it WILL NOT LIST ALL the missing arguments
            # at once INSTEAD only 1 missing argument at a time
            missing_arg = message.split()[1]
            print(_("Missing argument:\n%s") % missing_arg)
        sys.exit(2)


def pretty_float_formatter(field, ndigits=None):
    """Create a float value formatter function for the given field.

    :param field: str name of an object, which value should be formatted
    :param ndigits: int number of digits after decimal point to round
                    default is None - this disables rounding
    :returns: field formatter function
    """
    def _formatter(obj):
        value = obj[field] if type(obj) == dict else getattr(obj, field)
        if type(value) in (int, float):
            if ndigits:
                return round(value, ndigits)
            return value
        return "n/a"
    return _formatter


def args(*args, **kwargs):
    def _decorator(func):
        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        if "metavar" not in kwargs and "action" not in kwargs:
            # NOTE(andreykurilin): argparse constructs awful metavars...
            kwargs["metavar"] = "<%s>" % args[0].replace(
                "--", "").replace("-", "_")
        return func
    return _decorator


def alias(command_name):
    """Allow cli to use alias command name instead of function name.

    :param command_name: desired command name
    """
    def decorator(func):
        func.alias = command_name
        return func
    return decorator


def deprecated_args(*args, **kwargs):
    def _decorator(func):
        if "release" not in kwargs:
            raise ValueError("'release' is required keyword argument of "
                             "'deprecated_args' decorator.")
        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        func.__dict__.setdefault("deprecated_args", [])
        func.deprecated_args.append(args[0])

        help_msg = "[Deprecated since Rally %s] " % kwargs.pop("release")
        if "alternative" in kwargs:
            help_msg += "Use '%s' instead. " % kwargs.pop("alternative")
        if "help" in kwargs:
            help_msg += kwargs["help"]
        kwargs["help"] = help_msg
        return func
    return _decorator


def _methods_of(cls):
    """Get all callable methods of a class that don't start with underscore.

    :returns: a list of tuples of the form (method_name, method)
    """
    # The idea of unbound methods exists in Python 2 and was removed in
    # Python 3, so "inspect.ismethod" is used here for Python 2 and
    # "inspect.isfunction" for Python 3.
    all_methods = inspect.getmembers(
        cls, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
    methods = [m for m in all_methods if not m[0].startswith("_")]
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
            name = getattr(item[1], "alias", item[0])
            if item[1].__doc__:
                doc = info.parse_docstring(
                    item[1].__doc__)["short_description"]
            else:
                doc = ""
            name += " " * (first_column_len - len(name))
            description += "   %s%s\n" % (name, doc)

    return description


def _compose_action_description(action_fn):
    description = ""
    if action_fn.__doc__:
        parsed_doc = info.parse_docstring(action_fn.__doc__)
        short = parsed_doc.get("short_description")
        long = parsed_doc.get("long_description")

        description = "%s\n\n%s" % (short, long) if long else short

    return description


def _add_command_parsers(categories, subparsers):

    # INFO(oanufriev) This monkey patching makes our custom parser class to be
    # used instead of native.  This affects all subparsers down from
    # 'subparsers' parameter of this function (categories and actions).
    subparsers._parser_class = CategoryParser

    parser = subparsers.add_parser("version")

    parser = subparsers.add_parser("bash-completion")
    parser.add_argument("query_category", nargs="?")

    for category in categories:
        command_object = categories[category]()
        descr = _compose_category_description(categories[category])
        parser = subparsers.add_parser(
            category, description=descr,
            formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.set_defaults(command_object=command_object)

        category_subparsers = parser.add_subparsers(dest="action")

        for method_name, method in _methods_of(command_object):
            descr = _compose_action_description(method)
            parser = category_subparsers.add_parser(
                getattr(method, "alias", method_name),
                formatter_class=argparse.RawDescriptionHelpFormatter,
                description=descr, help=descr)

            action_kwargs = []
            for args, kwargs in getattr(method, "args", []):
                # FIXME(markmc): hack to assume dest is the arg name without
                # the leading hyphens if no dest is supplied
                kwargs.setdefault("dest", args[0][2:])
                action_kwargs.append(kwargs["dest"])
                kwargs["dest"] = "action_kwarg_" + kwargs["dest"]
                parser.add_argument(*args, **kwargs)

            parser.set_defaults(action_fn=method)
            parser.set_defaults(action_kwargs=action_kwargs)
            parser.add_argument("action_args", nargs="*")


def validate_deprecated_args(argv, fn):
    if (len(argv) > 3
       and (argv[2] == fn.__name__)
       and getattr(fn, "deprecated_args", None)):
        for item in fn.deprecated_args:
            if item in argv[3:]:
                LOG.warning("Deprecated argument %s for %s." % (item,
                                                                fn.__name__))


def run(argv, categories):
    parser = lambda subparsers: _add_command_parsers(categories, subparsers)
    category_opt = cfg.SubCommandOpt("category",
                                     title="Command categories",
                                     help="Available categories",
                                     handler=parser)

    CONF.register_cli_opt(category_opt)
    help_msg = ("Additional custom plugin locations. Multiple files or "
                "directories may be specified. All plugins in the specified"
                " directories and subdirectories will be imported. Plugins in"
                " /opt/rally/plugins and ~/.rally/plugins will always be "
                "imported.")

    CONF.register_cli_opt(cfg.ListOpt("plugin-paths",
                                      default=os.environ.get(
                                          "RALLY_PLUGIN_PATHS"),
                                      help=help_msg))

    try:
        CONF(argv[1:], project="rally", version=version.version_string(),
             default_config_files=find_config_files(CONFIG_SEARCH_PATHS))
        logging.setup("rally")
        if not CONF.get("log_config_append"):
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

            LOG.debug("urllib3 insecure warnings are hidden.")
            for warning in ("InsecurePlatformWarning",
                            "SNIMissingWarning",
                            "InsecureRequestWarning"):
                warning_cls = getattr(urllib3.exceptions, warning, None)
                if warning_cls is not None:
                    urllib3.disable_warnings(warning_cls)

            # NOTE(wtakase): This is for suppressing boto error logging.
            LOG.debug("ERROR log from boto module is hide.")
            boto_log = logging.getLogger("boto").logger
            boto_log.setLevel(logging.CRITICAL)

    except cfg.ConfigFilesNotFoundError:
        cfgfile = CONF.config_file[-1] if CONF.config_file else None
        if cfgfile and not os.access(cfgfile, os.R_OK):
            st = os.stat(cfgfile)
            print(_("Could not read %s. Re-running with sudo") % cfgfile)
            try:
                os.execvp("sudo", ["sudo", "-u", "#%s" % st.st_uid] + sys.argv)
            except Exception:
                print(_("sudo failed, continuing as if nothing happened"))

        print(_("Please re-run %s as root.") % argv[0])
        return(2)

    if CONF.category.name == "version":
        print(version.version_string())
        return(0)

    if CONF.category.name == "bash-completion":
        print(_generate_bash_completion_script())
        return(0)

    fn = CONF.category.action_fn
    fn_args = [encodeutils.safe_decode(arg)
               for arg in CONF.category.action_args]
    fn_kwargs = {}
    for k in CONF.category.action_kwargs:
        v = getattr(CONF.category, "action_kwarg_" + k)
        if v is None:
            continue
        if isinstance(v, six.string_types):
            v = encodeutils.safe_decode(v)
        fn_kwargs[k] = v

    # call the action with the remaining arguments
    # check arguments
    try:
        validate_args(fn, *fn_args, **fn_kwargs)
    except MissingArgs as e:
        # NOTE(mikal): this isn't the most helpful error message ever. It is
        # long, and tells you a lot of things you probably don't want to know
        # if you just got a single arg wrong.
        print(fn.__doc__)
        CONF.print_help()
        print("Missing arguments:")
        for missing in e.missing:
            for arg in fn.args:
                if arg[1].get("dest", "").endswith(missing):
                    print(" " + arg[0][0])
                    break
        return(1)

    try:
        for path in CONF.plugin_paths or []:
            discover.load_plugins(path)

        validate_deprecated_args(argv, fn)

        if getattr(fn, "_suppress_warnings", False):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ret = fn(*fn_args, **fn_kwargs)
        else:
            ret = fn(*fn_args, **fn_kwargs)
        return(ret)

    except (IOError, TypeError, ValueError, exceptions.DeploymentNotFound,
            exceptions.TaskNotFound, jsonschema.ValidationError) as e:
        if logging.is_debug():
            LOG.exception(e)
        print(e)
        return 1
    except sqlalchemy.exc.OperationalError as e:
        if logging.is_debug():
            LOG.exception(e)
        print(e)
        print("Looks like Rally can't connect to its DB.")
        print("Make sure that connection string in rally.conf is proper:")
        print(CONF.database.connection)
        return 1
    except Exception:
        print(_("Command failed, please check log for more info"))
        raise


def _generate_bash_completion_script():
    from rally.cli import main
    bash_data = """#!/bin/bash

# Standalone _filedir() alternative.
# This exempts from dependence of bash completion routines
function _rally_filedir()
{
    test "${1}" \\
        && COMPREPLY=( \\
            $(compgen -f -- "${cur}" | grep -E "${1}") \\
            $(compgen -o plusdirs -- "${cur}") ) \\
        || COMPREPLY=( \\
            $(compgen -o plusdirs -f -- "${cur}") \\
            $(compgen -d -- "${cur}") )
}

_rally()
{
    declare -A SUBCOMMANDS
    declare -A OPTS

%(data)s
    for OPT in ${!OPTS[*]} ; do
        CMD=${OPT%%%%_*}
        CMDSUB=${OPT#*_}
        SUBCOMMANDS[${CMD}]+="${CMDSUB} "
    done

    COMMANDS="${!SUBCOMMANDS[*]}"
    COMPREPLY=()

    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    if [[ $cur =~ ^(\.|\~|\/) ]] || [[ $prev =~ ^--out(|put-file)$ ]] ; then
        _rally_filedir
    elif [[ $prev =~ ^--(task|filename)$ ]] ; then
        _rally_filedir "\\.json|\\.yaml|\\.yml"
    elif [ $COMP_CWORD == "1" ] ; then
        COMPREPLY=($(compgen -W "$COMMANDS" -- ${cur}))
    elif [ $COMP_CWORD == "2" ] ; then
        COMPREPLY=($(compgen -W "${SUBCOMMANDS[${prev}]}" -- ${cur}))
    else
        COMMAND="${COMP_WORDS[1]}_${COMP_WORDS[2]}"
        COMPREPLY=($(compgen -W "${OPTS[$COMMAND]}" -- ${cur}))
    fi
    return 0
}

complete -o filenames -F _rally rally
"""
    completion = []
    for category, cmds in main.categories.items():
        for name, command in _methods_of(cmds):
            command_name = getattr(command, "alias", name)
            args_list = []
            for arg in getattr(command, "args", []):
                if getattr(command, "deprecated_args", []):
                    if arg[0][0] not in command.deprecated_args:
                        args_list.append(arg[0][0])
                else:
                    args_list.append(arg[0][0])
            args = " ".join(args_list)

            completion.append("""    OPTS["{cat}_{cmd}"]="{args}"\n""".format(
                cat=category, cmd=command_name, args=args))
    return bash_data % {"data": "".join(sorted(completion))}
