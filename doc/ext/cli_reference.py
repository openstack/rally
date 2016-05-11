# Copyright 2016: Mirantis Inc.
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

import copy
import inspect

from docutils.parsers import rst

from rally.cli import cliutils
from rally.cli import main
from rally.cli import manage
from utils import (category, subcategory, hint, make_definition, note,
                   paragraph, parse_text, warning)


class Parser(object):
    """A simplified interface of argparse.ArgumentParser"""
    def __init__(self):
        self.parsers = {}
        self.subparser = None
        self.defaults = {}
        self.arguments = []

    def add_parser(self, name, help=None, description=None,
                   formatter_class=None):
        parser = Parser()
        self.parsers[name] = {"description": description,
                              "help": help,
                              "fclass": formatter_class,
                              "parser": parser}
        return parser

    def set_defaults(self, command_object=None, action_fn=None,
                     action_kwargs=None):
        if command_object:
            self.defaults["command_object"] = command_object
        if action_fn:
            self.defaults["action_fn"] = action_fn
        if action_kwargs:
            self.defaults["action_kwargs"] = action_kwargs

    def add_subparsers(self, dest):
        # NOTE(andreykurilin): there is only one expected call
        if self.subparser:
            raise ValueError("Can't add one more subparser.")
        self.subparser = Parser()
        return self.subparser

    def add_argument(self, *args, **kwargs):
        if "action_args" in args:
            return
        self.arguments.append((args, kwargs))


DEFAULT_UUIDS_CMD = {
    "deployment": ["rally deployment create"],
    "task": ["rally task start"],
    "verification": ["rally verify start", "rally verify import_results"]
}


def compose_note_about_default_uuids(argument, dest):
    # TODO(andreykurilin): add references to commands
    return note("The default value for the ``%(arg)s`` argument is taken from "
                "the Rally environment. Usually, the default value is equal to"
                " the UUID of the last successful run of ``%(cmd)s``, if the "
                "``--no-use`` argument was not used." % {
                    "arg": argument,
                    "cmd": "``, ``".join(DEFAULT_UUIDS_CMD[dest])})


def compose_use_cmd_hint_msg(cmd):
    return hint("You can set the default value by executing ``%(cmd)s <uuid>``"
                " (ref__).\n\n __ #%(ref)s" % {"cmd": cmd,
                                               "ref": cmd.replace(" ", "-")})


def make_arguments_section(category_name, cmd_name, arguments, defaults):
    elements = [paragraph("**Command arguments**:")]
    for args, kwargs in arguments:
        # for future changes...
        # :param args: a single command argument which can represented by
        #       several names(for example, --uuid and --task-id) in cli.
        # :type args: tuple
        # :param kwargs: description of argument. Have next format:
        #       {"dest": "action_kwarg_<name of keyword argument in code>",
        #        "help": "just a description of argument"
        #        "metavar": "[optional] metavar of argument. Example:"
        #                      "Example: argument '--file'; metavar 'path' ",
        #        "type": "[optional] class object of argument's type",
        #        "required": "[optional] boolean value"}
        # :type kwargs: dict
        dest = kwargs.get("dest").replace("action_kwarg_", "")
        description = []
        if cmd_name != "use":
            # lets add notes about specific default values and hint about
            # "use" command with reference
            if dest in ("deployment", "task"):
                description.append(compose_note_about_default_uuids(
                        args[0], dest))
                description.append(
                        compose_use_cmd_hint_msg("rally %s use" % dest))
            elif dest == "verification":
                description.append(compose_note_about_default_uuids(
                        args[0], dest))
                description.append(
                        compose_use_cmd_hint_msg("rally verify use"))

        description.append(kwargs.get("help"))

        action = kwargs.get("action")
        if not action:
            arg_type = kwargs.get("type")
            if arg_type:
                description.append("**Type**: %s" % arg_type.__name__)

            skip_default = dest in ("deployment",
                                    "task_id",
                                    "verification")
            if not skip_default and dest in defaults:
                description.append("**Default**: %s" % defaults[dest])
        metavar = kwargs.get("metavar")

        ref = "%s_%s_%s" % (category_name, cmd_name, args[0].replace("-", ""))

        if metavar:
            args = ["%s %s" % (arg, metavar) for arg in args]

        elements.extend(make_definition(", ".join(args), ref, description))
    return elements


def get_defaults(func):
    """Return a map of argument:default_value for specified function."""
    spec = inspect.getargspec(func)
    if spec.defaults:
        return dict(zip(spec.args[-len(spec.defaults):], spec.defaults))
    return {}


def make_command_section(category_name, name, parser):
    # NOTE(andreykurilin): there is only one category in rally-manage, so
    # let's just hardcode it.
    cmd = "rally-manage" if category_name == "db" else "rally"
    section = subcategory("%s %s %s" % (cmd, category_name, name))
    section.extend(parse_text(parser["description"]))
    if parser["parser"].arguments:
        defaults = get_defaults(parser["parser"].defaults["action_fn"])
        section.extend(make_arguments_section(
            category_name, name, parser["parser"].arguments, defaults))
    return section


def make_category_section(name, parser):
    category_obj = category("Category: %s" % name)
    # NOTE(andreykurilin): we are re-using `_add_command_parsers` method from
    # `rally.cli.cliutils`, but, since it was designed to print help message,
    # generated description for categories contains specification for all
    # sub-commands. We don't need information about sub-commands at this point,
    # so let's skip "generated description" and take it directly from category
    # class.
    description = parser.defaults["command_object"].__doc__
    # TODO(andreykurilin): write a decorator which will mark cli-class as
    #   deprecated without changing its docstring.
    if description.startswith("[Deprecated"):
        i = description.find("]")
        msg = description[1:i]
        description = description[i+1:].strip()
        category_obj.append(warning(msg))
    category_obj.extend(parse_text(description))

    for command in sorted(parser.subparser.parsers.keys()):
        subparser = parser.subparser.parsers[command]
        category_obj.append(make_command_section(name, command, subparser))
    return category_obj


class CLIReferenceDirective(rst.Directive):

    def run(self):
        parser = Parser()
        categories = copy.copy(main.categories)
        categories["db"] = manage.DBCommands
        cliutils._add_command_parsers(categories, parser)

        content = []
        for category in sorted(categories.keys()):
            content.append(make_category_section(
                category, parser.parsers[category]["parser"]))
        return content


def setup(app):
    app.add_directive("make_cli_reference", CLIReferenceDirective)
