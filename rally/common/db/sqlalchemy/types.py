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

import collections
import json

from sqlalchemy.dialects import mysql as mysql_types
from sqlalchemy.ext import mutable
from sqlalchemy import types as sa_types


class TimeStamp(sa_types.TypeDecorator):
    """Represents datetime/time timestamp object as a bigint value.

    Despite the fact that timestamp objects are represented by float value in
    python, the Float column cannot be used for storing such values, since
    timestamps values can be bigger than the limit of Float columns at some
    back-ends (the value will be cropped in such case). Also, using Datetime
    type is not convenient too, since it do not accurate with microseconds.
    """

    impl = sa_types.BigInteger
    _coefficient = 1000000.0

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value * self._coefficient

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value / self._coefficient

    def compare_against_backend(self, dialect, conn_type):
        return isinstance(conn_type, sa_types.BIGINT)


class LongText(sa_types.TypeDecorator):
    """Represents an immutable structure as a json-encoded string.

       MySql can store only 64kb in Text type, and for example in psql or
       sqlite we are able to store more than 1GB. In some cases, like storing
       results of task 64kb is not enough. So this type uses for MySql
       LONGTEXT that allows us to store 4GiB.
    """

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql_types.LONGTEXT)
        else:
            return dialect.type_descriptor(sa_types.Text)


class JSONEncodedDict(LongText):
    """Represents an immutable structure as a json-encoded string."""

    impl = sa_types.Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value, sort_keys=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(
                value, object_pairs_hook=collections.OrderedDict)
        return value


class JSONEncodedList(JSONEncodedDict):
    """Represents an immutable structure as a json-encoded string."""

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutableDict(mutable.Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to MutableDict."""

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return mutable.Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""

        dict.__delitem__(self, key)
        self.changed()


class MutableList(mutable.Mutable, list):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain lists to MutableList."""
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)

            # this call will raise ValueError
            return mutable.Mutable.coerce(key, value)
        else:
            return value

    def append(self, value):
        """Detect list add events and emit change events."""
        list.append(self, value)
        self.changed()

    def remove(self, value):
        """Removes an item by value and emit change events."""
        list.remove(self, value)
        self.changed()

    def __setitem__(self, key, value):
        """Detect list set events and emit change events."""
        list.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, i):
        """Detect list del events and emit change events."""
        list.__delitem__(self, i)
        self.changed()


class MutableJSONEncodedList(JSONEncodedList):
    """Represent a mutable structure as a json-encoded string."""


class MutableJSONEncodedDict(JSONEncodedDict):
    """Represent a mutable structure as a json-encoded string."""


MutableDict.associate_with(MutableJSONEncodedDict)
MutableList.associate_with(MutableJSONEncodedList)
