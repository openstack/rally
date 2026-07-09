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

from rally.cli.commands import db
from rally.cli.commands import deployment
from rally.cli.commands import env
from rally.cli.commands import plugin
from rally.cli.commands import task
from rally.cli.commands import verify
from rally.common.plugin import info
from tests.unit import test


APPS = [db.db_app, deployment.deployment_app, env.env_app, plugin.plugin_app,
        task.task_app, verify.verify_app]


class DocstringsTestCase(test.TestCase):

    def test_params(self):
        for app in APPS:
            for command in app.registered_commands:
                func = command.callback
                if func is None or func.__doc__ is None:
                    continue
                m_info = info.parse_docstring(func.__doc__)
                if m_info["params"]:
                    self.fail("The description of parameters for CLI commands "
                              "should be passed as the 'help' argument of a "
                              "`typer.Option`/`typer.Argument`. You should "
                              "remove the parameter descriptions from the "
                              "docstring of `%s:%s`" % (func.__module__,
                                                        func.__qualname__))
