# Copyright 2014: Mirantis Inc.
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

from rally.common import logging
from rally.plugins.openstack import credential


LOG = logging.getLogger(__name__)


class Credential(credential.OpenStackCredential):
    """Deprecated version of OpenStackCredential class"""
    def __init__(self, *args, **kwargs):
        super(Credential, self).__init__(*args, **kwargs)
        LOG.warning("Class rally.common.objects.Credential is deprecated "
                    "since Rally 0.11.0. Use raw dict for OpenStack "
                    "credentials instead.")

    def to_dict(self, include_permission=False):
        dct = super(Credential, self).to_dict()
        if not include_permission:
            dct.pop("permission")
        return dct
