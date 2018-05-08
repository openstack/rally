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

import os

import requests

from rally.common.plugin import plugin
from rally import exceptions
from rally.task import types


@plugin.configure(name="path_or_url")
class PathOrUrl(types.ResourceType):
    """Check whether file exists or url available."""

    def pre_process(self, resource_spec, config):
        path = os.path.expanduser(resource_spec)
        if os.path.isfile(path):
            return path
        try:
            head = requests.head(path)
            if head.status_code == 200:
                return path
            raise exceptions.InvalidScenarioArgument(
                "Url %s unavailable (code %s)" % (path, head.status_code))
        except Exception as ex:
            raise exceptions.InvalidScenarioArgument(
                "Url error %s (%s)" % (path, ex))


@plugin.configure(name="file")
class FileType(types.ResourceType):
    """Return content of the file by its path."""

    def pre_process(self, resource_spec, config):
        with open(os.path.expanduser(resource_spec), "r") as f:
            return f.read()


@plugin.configure(name="expand_user_path")
class ExpandUserPath(types.ResourceType):
    """Expands user path."""

    def pre_process(self, resource_spec, config):
        return os.path.expanduser(resource_spec)


@plugin.configure(name="file_dict")
class FileTypeDict(types.ResourceType):
    """Return the dictionary of items with file path and file content."""

    def pre_process(self, resource_spec, config):
        file_type_dict = {}
        for file_path in resource_spec:
            file_path = os.path.expanduser(file_path)
            with open(file_path, "r") as f:
                file_type_dict[file_path] = f.read()

        return file_type_dict
