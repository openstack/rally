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

from pecan import rest
import wsmeext.pecan as wsme_pecan

from rally.api import types


class Version(types.Version):
    @classmethod
    def convert(cls):
        v = super(Version, cls).convert('v1', 'CURRENT',
                                        updated_at='2014-01-07T00:00:00Z')
        return v


class Controller(rest.RestController):
    """Version 1 API Controller Root."""

    @wsme_pecan.wsexpose(Version)
    def get(self):
        return Version.convert()
