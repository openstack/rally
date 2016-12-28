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

from rally.task import context

configure = context.configure


class VerifierContext(context.Context):
    """Verifier context that will be run before starting a verification."""

    def __init__(self, ctx):
        super(VerifierContext, self).__init__(ctx)

        # There is no term "task" in verification.
        del self.task
        self.verification = self.context.get("verification", {})
        self.verifier = self.context["verifier"]

    @classmethod
    def _meta_get(cls, key, default=None):
        # It should be always hidden
        if key == "hidden":
            return True
        return super(VerifierContext, cls)._meta_get(key, default)


class ContextManager(context.ContextManager):

    @staticmethod
    def validate(ctx, non_hidden=False):
        for name, config in ctx.items():
            VerifierContext.get(name).validate(config, non_hidden=non_hidden)

    def _get_sorted_context_lst(self):
        return sorted([VerifierContext.get(name)(self.context_obj)
                       for name in self.context_obj["config"].keys()])
