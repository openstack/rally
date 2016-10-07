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

import jinja2


def get_template(template):

    def include_raw_file(file_name):
        try:
            return jinja2.Markup(loader.get_source(env, file_name)[0])
        except jinja2.TemplateNotFound:
            # NOTE(amaretskiy): re-raise error to make its message clear
            raise IOError("File not found: %s" % file_name)

    loader = jinja2.PackageLoader("rally.ui", "templates")
    env = jinja2.Environment(loader=loader)
    env.globals["include_raw_file"] = include_raw_file

    return env.get_template(template)
