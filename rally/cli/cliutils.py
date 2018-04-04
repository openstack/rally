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
import json
import os
import sys
import textwrap
import warnings

import jsonschema
import prettytable
import six
import sqlalchemy.exc

from rally import api
from rally.common import cfg
from rally.common import logging
from rally.common.plugin import info
from rally import exceptions
from rally.utils import encodeutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


# Some CLI-specific constants
MARGIN = 3


class MissingArgs(Exception):
    """Supplied arguments are not sufficient for calling a function."""
    def __init__(self, missing):
        self.missing = missing
        msg = "Missing arguments: %s" % ", ".join(missing)
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
        raise ValueError("Field labels list %(labels)s has different number of"
                         " elements than fields list %(fields)s"
                         % {"labels": field_labels, "fields": fields})

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
                field_name = field

                if normalize_field_names:
                    if field_name not in mixed_case_fields:
                        field_name = field_name.lower()
                    field_name = field_name.replace(" ", "_").replace("-", "_")

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


def print_dict(obj, fields=None, formatters=None, mixed_case_fields=False,
               normalize_field_names=False, property_label="Property",
               value_label="Value", table_label=None, print_header=True,
               print_border=True, wrap=0, out=sys.stdout):
    """Print dict as a table.

    :param obj: dict to print
    :param fields: `dict` of keys to print from d. Defaults to all keys
    :param formatters: `dict` of callables for field formatting
    :param mixed_case_fields: fields corresponding to object attributes that
        have mixed case names (e.g., 'serverId')
    :param normalize_field_names: If True, field names will be transformed,
        e.g. "Field Name" -> "field_name", otherwise they will be used
        unchanged.
    :param property_label: label of "property" column
    :param value_label: label of "value" column
    :param table_label: Label to use as header for the whole table.
    :param print_header: print table header.
    :param print_border: print table border.
    :param out: stream to write output to.
    """
    formatters = formatters or {}
    mixed_case_fields = mixed_case_fields or []
    if not fields:
        if isinstance(obj, dict):
            fields = sorted(obj.keys())
        else:
            fields = [name for name in dir(obj)
                      if (not name.startswith("_") and
                          not callable(getattr(obj, name)))]

    pt = prettytable.PrettyTable([property_label, value_label], caching=False)
    pt.align = "l"
    for field_name in fields:
        if field_name in formatters:
            data = formatters[field_name](obj)
        else:
            field = field_name
            if normalize_field_names:
                if field not in mixed_case_fields:
                    field = field_name.lower()
                field = field.replace(" ", "_").replace("-", "_")

            if isinstance(obj, dict):
                data = obj.get(field, "")
            else:
                data = getattr(obj, field, "")

        # convert dict to str to check length
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        if wrap > 0:
            data = textwrap.fill(six.text_type(data), wrap)
        # if value has a newline, add in multiple rows
        # e.g. fault with stacktrace
        if (data and
                isinstance(data, six.string_types) and
                (r"\n" in data or "\r" in data)):
            # "\r" would break the table, so remove it.
            if "\r" in data:
                data = data.replace("\r", "")
            lines = data.strip().split(r"\n")
            col1 = field_name
            for line in lines:
                pt.add_row([col1, line])
                col1 = ""
        else:
            if data is None:
                data = "-"
            pt.add_row([field_name, data])

    table_body = pt.get_string(header=print_header,
                               border=print_border) + "\n"

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
        raise ValueError(
            "Table header %s is longer than total width of the table.")

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
    header += "%s\n" % text
    header += symbol * size + "\n"
    return header


def suppress_warnings(f):
    f._suppress_warnings = True
    return f


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
            print("Missing argument:\n%s" % missing_arg)
        sys.exit(2)


def pretty_float_formatter(field, ndigits=None):
    """Create a float value formatter function for the given field.

    :param field: str name of an object, which value should be formatted
    :param ndigits: int number of digits after decimal point to round
                    default is None - this disables rounding
    :returns: field formatter function
    """
    def _formatter(obj):
        value = obj[field] if isinstance(obj, dict) else getattr(obj, field)
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
        release = kwargs.pop("release")
        alternative = kwargs.pop("alternative", None)

        help_msg = "[Deprecated since Rally %s] " % release
        if alternative:
            help_msg += "Use '%s' instead. " % alternative
        if "help" in kwargs:
            help_msg += kwargs["help"]
        kwargs["help"] = help_msg

        func.__dict__.setdefault("args", []).insert(0, (args, kwargs))
        func.__dict__.setdefault("deprecated_args", {})
        func.deprecated_args[args[0]] = (release, alternative)
        return func
    return _decorator


def help_group(uuid):
    """Label cli method with specific group.

    Joining methods by groups allows to compose more user-friendly help
    messages in CLI.

    :param uuid: Name of group to find common methods. It will be used for
        sorting groups in help message, so you can start uuid with
        some number (i.e "1_launcher", "2_management") to put groups in proper
        order. Note: default group had "0" uuid.
    """

    def wrapper(func):
        func.help_group = uuid
        return func
    return wrapper


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

    help_groups = {}
    for m in methods:
        group = getattr(m[1], "help_group", "0")
        help_groups.setdefault(group, []).append(m)

    if len(help_groups) > 1:
        # we should sort methods by groups
        methods = []
        for group in sorted(help_groups.items(), key=lambda x: x[0]):
            if methods:
                # None -> empty line between groups
                methods.append((None, None))
            methods.extend(group[1])
    return methods


def _compose_category_description(category):

    descr_pairs = _methods_of(category)

    description = ""
    doc = category.__doc__
    if doc:
        description = doc.strip()
    if descr_pairs:
        description += "\n\nCommands:\n"
        sublen = lambda item: len(item[0]) if item[0] else 0
        first_column_len = max(map(sublen, descr_pairs)) + MARGIN
        for item in descr_pairs:
            if item[0] is None:
                description += "\n"
                continue
            name = getattr(item[1], "alias", item[0].replace("_", "-"))
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
            if method is None:
                continue
            method_name = method_name.replace("_", "-")
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
        for item, details in fn.deprecated_args.items():
            if item in argv[3:]:
                msg = ("The argument `%s` is deprecated since Rally %s." %
                       (item, details[0]))
                if details[1]:
                    msg += " Use `%s` instead." % details[1]
                LOG.warning(msg)


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

    # NOTE(andreykurilin): this dirty hack is done to unblock the gates.
    #   Currently, we are using oslo.config for CLI purpose (don't do this!)
    #   and it makes the things too complicated.
    #   To discover which CLI method can be affected by warnings and which not
    #   (based on suppress_warnings decorator) we need to obtain a desired
    #   CLI method. It can be done only after initialization of oslo_config
    #   which is located in rally.api.API init method.
    #   Initialization of rally.api.API can produce a warning (for example,
    #   from pymysql), so suppressing of warnings later will not work in such
    #   case (it is what actually had happened now in our CI with the latest
    #   release of PyMySQL).
    #
    # https://bitbucket.org/zzzeek/sqlalchemy/issues/4120/mysql-5720-warns-on-tx_isolation
    try:
        import pymysql
        warnings.filterwarnings("ignore", category=pymysql.Warning)
    except ImportError:
        pass

    try:
        rapi = api.API(config_args=argv[1:], skip_db_check=True)
    except exceptions.RallyException as e:
        print(e)
        return(2)

    if CONF.category.name == "version":
        print(CONF.version)
        return(0)

    if CONF.category.name == "bash-completion":
        print(_generate_bash_completion_script())
        return(0)

    fn = CONF.category.action_fn
    fn_args = [encodeutils.safe_decode(arg)
               for arg in CONF.category.action_args]
    # api instance always is the first argument
    fn_args.insert(0, rapi)
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
        validate_deprecated_args(argv, fn)

        # skip db check for db and plugin commands
        if CONF.category.name not in ("db", "plugin"):
            rapi.check_db_revision()

        if getattr(fn, "_suppress_warnings", False):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ret = fn(*fn_args, **fn_kwargs)
        else:
            ret = fn(*fn_args, **fn_kwargs)
        return ret

    except (IOError, TypeError, ValueError,
            exceptions.RallyException, jsonschema.ValidationError) as e:
        if logging.is_debug():
            LOG.exception("Unexpected exception in CLI")
        else:
            print(e)
        return getattr(e, "error_code", 1)
    except sqlalchemy.exc.OperationalError as e:
        if logging.is_debug():
            LOG.exception("Something went wrong with database")
        print(e)
        print("Looks like Rally can't connect to its DB.")
        print("Make sure that connection string in rally.conf is proper:")
        print(CONF.database.connection)
        return 1
    except Exception:
        print("Command failed, please check log for more info")
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
            if name is None:
                continue
            command_name = getattr(command, "alias", name.replace("_", "-"))
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
