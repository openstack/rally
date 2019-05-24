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

import functools
import re

from rally.common.plugin import plugin
from rally.task import context

# all VerifierContexts should be always hidden
configure = functools.partial(context.configure, hidden=True)


def _expand_skip_list(load_list, regexps):
    """Returns mapping of test names to the reason why the test was skipped.

    The dictionary includes all tests in``load_list`` that match a key in
    ``regexps``.
    """
    result = {}
    if not regexps:
        return result
    for regex, reason in regexps.items():
        try:
            pattern = re.compile(regex)
            for test in load_list:
                if pattern.search(test):
                    result[test] = reason
        except re.error:
            # assume regex is a test id, eg: tempest.api.compute.admin.
            # test_flavors.FlavorsAdminTestJSON.
            # test_create_flavor_using_string_ram
            # [id-3b541a2e-2ac2-4b42-8b8d-ba6e22fcd4da]
            result[regex] = reason
            continue
    return result


@plugin.base()
class VerifierContext(context.BaseContext):
    """Verifier context that will be run before starting a verification."""

    def __init__(self, ctx):
        super(VerifierContext, self).__init__(ctx)
        self.verification = self.context.get("verification", {})
        self.verifier = self.context["verifier"]

    @classmethod
    def validate(cls, config):
        # do not validate jsonschema.
        pass

    def setup(self):
        self._process_runargs()

    def _process_runargs(self):
        # Store the skip and test lists in the context

        run_args = self.context.get("run_args", {})

        load_list = run_args.get("load_list")
        skip_list = run_args.get("skip_list")

        if skip_list:
            if not load_list:
                load_list = self.verifier.manager.list_tests()
            skip_list = _expand_skip_list(load_list, skip_list)

        self.context["skip_list"] = skip_list
        self.context["load_list"] = load_list
        self.context["xfail_list"] = run_args.get("xfail_list")


class ContextManager(context.ContextManager):

    @staticmethod
    def validate(ctx):
        for name, config in ctx.items():
            VerifierContext.get(name, allow_hidden=True).validate(config)

    def _get_sorted_context_lst(self):
        return sorted([
            VerifierContext.get(name, allow_hidden=True)(self.context_obj)
            for name in self.context_obj["config"].keys()])

    def _log_prefix(self):
        return "Verification %s |" % self.context_obj["verifier"]["uuid"]
