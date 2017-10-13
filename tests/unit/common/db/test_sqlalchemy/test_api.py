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

# NOTE(andreykurilin): most tests for sqlalchemy api is merged with db_api
#   tests. Hope, it will be fixed someday.

import collections
import datetime as dt

import ddt

from rally.common.db.sqlalchemy import api as db_api
from rally import exceptions
from tests.unit import test


NOW = dt.datetime.now()


class FakeSerializable(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _as_dict(self):
        return self.__dict__


@ddt.ddt
class SerializeTestCase(test.DBTestCase):

    @ddt.data(
        {"data": 1, "serialized": 1},
        {"data": 1.1, "serialized": 1.1},
        {"data": "a string", "serialized": "a string"},
        {"data": NOW, "serialized": NOW},
        {"data": {"k1": 1, "k2": 2}, "serialized": {"k1": 1, "k2": 2}},
        {"data": [1, "foo"], "serialized": [1, "foo"]},
        {"data": ["foo", 1, {"a": "b"}], "serialized": ["foo", 1, {"a": "b"}]},
        {"data": FakeSerializable(a=1), "serialized": {"a": 1}},
        {"data": [FakeSerializable(a=1),
                  FakeSerializable(b=FakeSerializable(c=1))],
         "serialized": [{"a": 1}, {"b": {"c": 1}}]},
    )
    @ddt.unpack
    def test_serialize(self, data, serialized):
        @db_api.serialize
        def fake_method():
            return data

        results = fake_method()
        self.assertEqual(serialized, results)

    def test_serialize_ordered_dict(self):
        data = collections.OrderedDict([(1, 2), ("foo", "bar"), (2, 3)])
        serialized = db_api.serialize_data(data)
        self.assertIsInstance(serialized, collections.OrderedDict)
        self.assertEqual([1, "foo", 2], list(serialized.keys()))
        self.assertEqual([2, "bar", 3], list(serialized.values()))

    def test_serialize_value_error(self):
        @db_api.serialize
        def fake_method():
            class Fake(object):
                pass

            return Fake()

        self.assertRaises(exceptions.DBException, fake_method)


class ModelQueryTestCase(test.DBTestCase):

    def test_model_query_wrong_model(self):

        class Foo(object):
            pass

        self.assertRaises(exceptions.DBException,
                          db_api.Connection().model_query, Foo)
