# Copyright 2017: Mirantis Inc.
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

import inspect

import jsonschema

from rally.common import validation


@validation.configure(name="jsonschema")
class JsonSchemaValidator(validation.Validator):
    """JSON schema validator"""

    def validate(self, credentials, config, plugin_cls, plugin_cfg):
        try:
            jsonschema.validate(plugin_cfg, plugin_cls.CONFIG_SCHEMA)
        except jsonschema.ValidationError as err:
            return self.fail(str(err))


@validation.configure(name="args-spec")
class ArgsValidator(validation.Validator):
    """Scenario arguments validator"""

    def validate(self, credentials, config, plugin_cls, plugin_cfg):
        scenario = plugin_cls
        name = scenario.get_name()
        namespace = scenario.get_namespace()
        if scenario.is_classbased:
            # We need initialize scenario class to access instancemethods
            scenario = scenario().run
        args, _varargs, varkwargs, defaults = inspect.getargspec(scenario)

        hint_msg = (" Use `rally plugin show --name %s --namespace %s` "
                    "to display scenario description." % (name, namespace))

        # scenario always accepts an instance of scenario cls as a first arg
        missed_args = args[1:]
        if defaults:
            # do not require args with default values
            missed_args = missed_args[:-len(defaults)]
        if "args" in config:
            missed_args = set(missed_args) - set(config["args"])
        if missed_args:
            msg = ("Argument(s) '%(args)s' should be specified in task config."
                   "%(hint)s" % {"args": "', '".join(missed_args),
                                 "hint": hint_msg})
            return self.fail(msg)

        if varkwargs is None and "args" in config:
            redundant_args = set(config["args"]) - set(args[1:])
            if redundant_args:
                msg = ("Unexpected argument(s) found ['%(args)s'].%(hint)s" %
                       {"args": "', '".join(redundant_args),
                        "hint": hint_msg})
                return self.fail(msg)
