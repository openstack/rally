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


class JSONEncodedDict(sa_types.TypeDecorator):
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


class BigJSONEncodedDict(JSONEncodedDict):
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
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


class MutableJSONEncodedDict(JSONEncodedDict):
    """Represent a mutable structure as a json-encoded string."""


class BigMutableJSONEncodedDict(BigJSONEncodedDict):
    """Represent a big mutable structure as a json-encoded string."""


MutableDict.associate_with(MutableJSONEncodedDict)
MutableDict.associate_with(BigMutableJSONEncodedDict)
