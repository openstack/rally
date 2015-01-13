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
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from rally.aas.rest.controllers import v1
from rally.aas.rest import types


class Root(wtypes.Base):

    name = wtypes.text
    description = wtypes.text
    versions = [types.Version]

    @classmethod
    def convert(self, name, description, versions):
        root = Root(name=name, description=description)
        root.versions = [v.get()["result"] for v in versions]
        return root


class RootController(rest.RestController):

    v1 = v1.Controller()

    @wsme_pecan.wsexpose(Root)
    def get(self):
        name = "OpenStack Rally API"
        description = ("Rally is a Benchmark-as-a-Service project for "
                       "OpenStack.")
        root = Root.convert(name, description, [self.v1])
        return root
