# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 IBM Corp.
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

from jsonschema import exceptions as schema_exceptions
import mock

from rally.benchmark.scenarios import utils
from tests import test


def action_one(self, *args, **kwargs):
    pass


def action_two(self, *args, **kwargs):
    pass


class ActionBuilderTestCase(test.TestCase):

    def setUp(self):
        super(ActionBuilderTestCase, self).setUp()
        self.mock_one = "%s.action_one" % __name__
        self.mock_two = "%s.action_two" % __name__

    def test_invalid_keyword(self):
        builder = utils.ActionBuilder(['action_one', 'action_two'])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.build_actions, [{'missing': 1}])

    def test_invalid_bind(self):
        builder = utils.ActionBuilder(['action_one'])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.bind_action, 'missing', action_one)

    def test_invalid_schema(self):
        builder = utils.ActionBuilder(['action_one', 'action_two'])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{'action_oone': 1},
                                             {'action_twoo': 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{'action_one': -1},
                                             {'action_two': 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{'action_one': 0},
                                             {'action_two': 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{1: 0},
                                             {'action_two': 2}])
        self.assertRaises(schema_exceptions.ValidationError,
                          builder.validate, [{'action_two': 'action_two'}])

    def test_positional_args(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(['action_one', 'action_two'])
                builder.bind_action('action_one', mock_action_one, 'a', 'b')
                builder.bind_action('action_two', mock_action_two, 'c')
                actions = builder.build_actions([{'action_two': 3},
                                                 {'action_one': 4}])
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call('a', 'b'))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call('c'))
        mock_action_two.assert_has_calls(mock_calls)

        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(['action_one', 'action_two'])
                builder.bind_action('action_one', mock_action_one, 'a', 'b')
                builder.bind_action('action_two', mock_action_two, 'c')
                actions = builder.build_actions([{'action_two': 3},
                                                 {'action_one': 4}],
                                                'd', 5)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call('a', 'b', 'd', 5))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call('c', 'd', 5))
        mock_action_two.assert_has_calls(mock_calls)

    def test_kwargs(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(['action_one', 'action_two'])
                builder.bind_action('action_one', mock_action_one, a=1, b=2)
                builder.bind_action('action_two', mock_action_two, c=3)
                actions = builder.build_actions([{'action_two': 3},
                                                 {'action_one': 4}])
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call(a=1, b=2))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call(c=3))
        mock_action_two.assert_has_calls(mock_calls)

        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(['action_one', 'action_two'])
                builder.bind_action('action_one', mock_action_one, a=1, b=2)
                builder.bind_action('action_two', mock_action_two, c=3)
                actions = builder.build_actions([{'action_two': 3},
                                                 {'action_one': 4}],
                                                d=4, e=5)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call(a=1, b=2, d=4, e=5))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call(c=3, d=4, e=5))
        mock_action_two.assert_has_calls(mock_calls)

    def test_mixed_args(self):
        with mock.patch(self.mock_one) as mock_action_one:
            with mock.patch(self.mock_two) as mock_action_two:
                builder = utils.ActionBuilder(['action_one', 'action_two'])
                builder.bind_action('action_one', mock_action_one, 'one',
                                    a=1, b=2)
                builder.bind_action('action_two', mock_action_two, 'two', c=3)
                actions = builder.build_actions([{'action_two': 3},
                                                 {'action_one': 4}],
                                                'three', d=4)
                for action in actions:
                    action()
        self.assertEqual(4, mock_action_one.call_count,
                         "action one not called 4 times")
        mock_calls = []
        for i in range(4):
            mock_calls.append(mock.call('one', 'three', a=1, b=2, d=4))
        mock_action_one.assert_has_calls(mock_calls)

        self.assertEqual(3, mock_action_two.call_count,
                         "action two not called 3 times")
        mock_calls = []
        for i in range(3):
            mock_calls.append(mock.call('two', 'three', c=3, d=4))
        mock_action_two.assert_has_calls(mock_calls)
