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

import jsonschema


class ActionBuilder(object):
    """Builder class for mapping and creating action objects into
    callable methods.

    An action list is an array of single key/value dicts which takes
    the form:

    [{'action': times}, {'action': times}...]

    Here 'action' is a string which indicates a action to perform and
    'times' is a non-zero positive integer which specifies how many
    times to run the action in sequence.

    This utility builder class will build and return methods which
    wrapper the action call the given amount of times.
    """

    SCHEMA_TEMPLATE = {
        "type": "array",
        "$schema": "http://json-schema.org/draft-03/schema",
        "items": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "minItems": 0
        }
    }

    ITEM_TEMPLATE = {
        "type": "integer",
        "minimum": 0,
        "exclusiveMinimum": True,
        "optional": True
    }

    def __init__(self, action_keywords):
        """Creates a new instance of the builder which supports the given
        action keywords.

        :param action_keywords: A list of strings which are the keywords this
        instance of the builder supports.
        """
        self._bindings = {}
        self.schema = dict(ActionBuilder.SCHEMA_TEMPLATE)
        for kw in action_keywords:
            self.schema['items']['properties'][kw] =\
                ActionBuilder.ITEM_TEMPLATE

    def bind_action(self, action_key, action, *args, **kwargs):
        """Binds an action and optionally static args/kwargs to an
        action key.

        :param action_key: The action keyword to bind the action to.
        :param action: A method/function to call for the action.
        :param args: (optional) Static positional args to prepend
        to all invocations of the action.
        :param kwargs: (optional) Static kwargs to prepend to all
        invocations of the action.
        """
        self.validate([{action_key: 1}])
        self._bindings[action_key] = {
            'action': action,
            'args': args or (),
            'kwargs': kwargs or {}
        }

    def validate(self, actions):
        """Validates the list of action objects against the schema
        for this builder.

        :param actions: The list of action objects to validate.
        """
        jsonschema.validate(actions, self.schema)

    def _build(self, func, times, *args, **kwargs):
        """Builds the wrapper action call."""
        def _f():
            for i in range(times):
                func(*args, **kwargs)
        return _f

    def build_actions(self, actions, *args, **kwargs):
        """Builds a list of callable actions based on the given
        action object list and the actions bound to this builder.

        :param actions: A list of action objects to build callable
        action for.
        :param args: (optional) Positional args to pass into each
        built action. These will be appended to any args set for the
        action via its binding.
        :param kwargs: (optional) Keyword args to pass into each built
        action. These will be appended to any kwards set for the action
        via its binding.
        """
        self.validate(actions)
        bound_actions = []
        for action in actions:
            action_key = action.keys()[0]
            times = action.get(action_key)
            binding = self._bindings.get(action_key)
            dft_kwargs = dict(binding['kwargs'])
            dft_kwargs.update(kwargs or {})
            bound_actions.append(self._build(
                                    binding['action'], times,
                                    *(binding['args'] + args), **dft_kwargs))
        return bound_actions
