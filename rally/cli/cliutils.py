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

"""Shared helpers for the Rally CLI."""

import contextvars
import functools
import json
import sys
import textwrap
import typing as t
import warnings

import prettytable
import typer.core

from rally.utils import encodeutils


if t.TYPE_CHECKING:
    import typer._click.core

    from rally.api import API


_api: "contextvars.ContextVar[API]" = contextvars.ContextVar("rally_api")


def set_api(api: "API") -> None:
    """Stash the per-invocation Rally API handle for the commands to read."""
    _api.set(api)


def get_api() -> "API":
    """Return the Rally API handle stashed by `set_api`."""
    return _api.get()


def iter_commands(
    command: "typer._click.core.Command",
) -> t.Iterator[
    tuple[
        tuple[str, ...],
        typer.core.TyperCommand,
        list[typer.core.TyperOption]
    ]
]:
    """Walk a built typer command tree and yield every leaf command.

    :param command: a resolved typer command, e.g. the result of
        `typer.main.get_command`. Groups are recursed into; for each leaf
        command the generator yields ``(path, leaf, params)`` where:

          * ``path`` is the tuple of command names from the root down to the
            leaf (the root group itself contributes no name), so
            ``rally task status`` yields
            ``("task", "status")`` and a top-level ``rally version`` yields
            ``("version",)``;
          * ``leaf`` is the `typer.core.TyperCommand` itself;
          * ``params`` is its option/argument list
    """
    if isinstance(command, typer.core.TyperGroup):
        for name, sub in command.commands.items():
            for path, leaf, params in iter_commands(sub):
                yield (name, *path), leaf, params
    else:
        leaf = t.cast(typer.core.TyperCommand, command)
        params = t.cast("list[typer.core.TyperOption]", leaf.params)
        yield (), leaf, params


def print_list(objs, fields, formatters=None, sortby_index=0,
               mixed_case_fields=None, field_labels=None,
               normalize_field_names=False,
               table_label=None, print_header=True, print_border=True,
               print_row_border=False,
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
    :param print_row_border: use border between rows
    :param out: stream to write output to.

    """
    formatters = formatters or {}
    mixed_case_fields = mixed_case_fields or []
    field_labels = field_labels or fields
    if len(field_labels) != len(fields):
        raise ValueError("Field labels list %(labels)s has different number of"
                         " elements than fields list %(fields)s"
                         % {"labels": field_labels, "fields": fields})

    kwargs = {}
    if sortby_index is not None:
        kwargs = {"sortby": field_labels[sortby_index]}

    if print_border and print_row_border:
        headers_horizontal_char = "="
        try:
            kwargs["hrules"] = prettytable.HRuleStyle.ALL
        except AttributeError:  # pragma: no cover
            # old prettytable
            kwargs["hrules"] = prettytable.ALL
    else:
        headers_horizontal_char = "-"
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
        try:
            pt.set_style(prettytable.TableStyle.PLAIN_COLUMNS)
        except AttributeError:  # pragma: no cover
            # old prettytable
            pt.set_style(prettytable.PLAIN_COLUMNS)
        pt.left_padding_width = 0
        pt.right_padding_width = 1

    table_body = pt.get_string(header=print_header,
                               border=print_border,
                               **kwargs) + "\n"
    if print_border and print_row_border:
        table_body = table_body.split("\n", 3)
        table_body[2] = table_body[2].replace("-", headers_horizontal_char)
        table_body = "\n".join(table_body)

    table_header = ""

    if table_label:
        table_width = table_body.index("\n")
        table_header = make_table_header(
            table_label, table_width, horizontal_char=headers_horizontal_char)
        table_header += "\n"

    if table_header:
        out.write(encodeutils.safe_encode(table_header).decode())
    out.write(encodeutils.safe_encode(table_body).decode())


def print_dict(
    obj: t.Any,
    fields: t.Sequence[str] | None = None,
    formatters: dict[str, t.Callable[[t.Any], t.Any]] | None = None,
    mixed_case_fields: t.Sequence[str] | None = None,
    normalize_field_names: bool = False,
    property_label: str = "Property",
    value_label: str = "Value",
    table_label: str | None = None,
    print_header: bool = True,
    print_border: bool = True,
    wrap: int = 0,
    out: t.IO[str] = sys.stdout,
) -> None:
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
                      if (not name.startswith("_")
                          and not callable(getattr(obj, name)))]

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
            data = textwrap.fill(str(data), wrap)
        # if value has a newline, add in multiple rows
        # e.g. fault with stacktrace
        if (data and isinstance(data, str)
                and (r"\n" in data or "\r" in data)):
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

    if table_header:
        out.write(encodeutils.safe_encode(table_header).decode())
    out.write(encodeutils.safe_encode(table_body).decode())


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


def make_header(text: str, size: int=80, symbol: str="-") -> str:
    """Unified way to make header message to CLI.

    :param text: what text to write
    :param size: Length of header decorative line
    :param symbol: What symbol to use to create header
    """
    return f"{symbol * size}\n{text}\n{symbol * size}\n"


def suppress_warnings(f):
    """Run the wrapped command with Python warnings silenced."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return f(*args, **kwargs)
    return wrapper


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
