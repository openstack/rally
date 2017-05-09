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


@validation.configure(name="required_params")
class RequiredParameterValidator(validation.Validator):
    """Scenario required parameter validator.

    This allows us to search required parameters in subdict of config.

    :param subdict: sub-dict of "config" to search. if
                    not defined - will search in "config"
    :param params: list of required parameters
    """

    def __init__(self, params=None, subdict=None):
        super(RequiredParameterValidator, self).__init__()
        self.subdict = subdict
        self.params = params

    def validate(self, credentials, config, plugin_cls, plugin_cfg):
        missing = []
        args = config.get("args", {})
        if self.subdict:
            args = args.get(self.subdict, {})
        for arg in self.params:
            if isinstance(arg, (tuple, list)):
                for case in arg:
                    if case in args:
                        break
                else:
                    missing.append(case)
            else:
                if arg not in args:
                    missing.append(arg)

        if missing:
            msg = ("%s parameters are not defined in "
                   "the benchmark config file") % ", ".join(missing)
            return self.fail(msg)


@validation.configure(name="number")
class NumberValidator(validation.Validator):
    """Checks that parameter is a number that pass specified condition.

    Ensure a parameter is within the range [minval, maxval]. This is a
    closed interval so the end points are included.

    :param param_name: Name of parameter to validate
    :param minval: Lower endpoint of valid interval
    :param maxval: Upper endpoint of valid interval
    :param nullable: Allow parameter not specified, or parameter=None
    :param integer_only: Only accept integers
    """

    def __init__(self, param_name, minval=None, maxval=None, nullable=False,
                 integer_only=False):
        self.param_name = param_name
        self.minval = minval
        self.maxval = maxval
        self.nullable = nullable
        self.integer_only = integer_only

    def validate(self, credentials, config, plugin_cls, plugin_cfg):

        value = config.get("args", {}).get(self.param_name)

        num_func = float
        if self.integer_only:
            # NOTE(boris-42): Force check that passed value is not float, this
            #   is important cause int(float_numb) won't raise exception
            if type(value) == float:
                return self.fail("%(name)s is %(val)s which hasn't int type"
                                 % {"name": self.param_name, "val": value})
            num_func = int

        # None may be valid if the scenario sets a sensible default.
        if self.nullable and value is None:
            return

        try:
            number = num_func(value)
            if self.minval is not None and number < self.minval:
                return self.fail(
                    "%(name)s is %(val)s which is less than the minimum "
                    "(%(min)s)" % {"name": self.param_name,
                                   "val": number,
                                   "min": self.minval})
            if self.maxval is not None and number > self.maxval:
                return self.fail(
                    "%(name)s is %(val)s which is greater than the maximum "
                    "(%(max)s)" % {"name": self.param_name,
                                   "val": number,
                                   "max": self.maxval})
        except (ValueError, TypeError):
            return self.fail("%(name)s is %(val)s which is not a valid "
                             "%(type)s" % {"name": self.param_name,
                                           "val": value,
                                           "type": num_func.__name__})
