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

from rally import consts
from rally.task import service as base_service


service = base_service.service
compat_layer = base_service.compat_layer
Service = base_service.Service
should_be_overridden = base_service.should_be_overridden


class UnifiedOpenStackService(base_service.UnifiedService):
    def discover_impl(self):
        impl_cls, impls = super(UnifiedOpenStackService, self).discover_impl()
        if not impl_cls:
            # Nova-network is not listed in keystone catalog and we can not
            # assume that it is enabled if neutron is missed. Since such
            # discovery needs an external call, it is done only if needed.
            for impl in impls:
                o = impl._meta_get("impl")
                if (o._meta_get("name") == consts.Service.NOVA_NET and
                        impl.is_applicable(self._clients)):
                    return impl, impls
        return impl_cls, impls
