# Copyright 2013: Intel Inc.
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

import mock
from oslo.config import cfg

from rally.cmd import cliutils
from rally.cmd.commands import deployment
from rally.cmd.commands import info
from rally.cmd.commands import show
from rally.cmd.commands import task
from rally.cmd.commands import use
from rally.cmd.commands import verify
from rally.openstack.common.apiclient import exceptions
from tests.unit import test

CONF = cfg.CONF


class CliUtilsTestCase(test.TestCase):

    def tearDown(self):
        self._unregister_opts()
        super(CliUtilsTestCase, self).tearDown()

    def test_pretty_float_formatter_rounding(self):
        test_table_rows = {"test_header": 6.56565}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header", 3)
        return_value = formatter(self)

        self.assertEqual(return_value, 6.566)

    def test_pretty_float_formatter_nonrounding(self):
        test_table_rows = {"test_header": 6.56565}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header")
        return_value = formatter(self)

        self.assertEqual(return_value, 6.56565)

    def test_pretty_float_formatter_none_value(self):
        test_table_rows = {"test_header": None}
        self.__dict__.update(**test_table_rows)

        formatter = cliutils.pretty_float_formatter("test_header")
        return_value = formatter(self)

        self.assertEqual(return_value, "n/a")

    def test__methods_of_works(self):
        class fake_class(object):
            pass

        def public_callable(self):
            pass

        def _private_callable(self):
            pass
        mock_obj = fake_class()
        mock_obj.public = public_callable
        mock_obj._private = _private_callable
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(1, len(result))
        self.assertEqual("public", result[0][0])

    def test__methods_of_empty_result(self):
        class fake_class():
            pass

        def public_callable(self):
            pass

        def _private_callable(self):
            pass

        mock_obj = fake_class()
        mock_obj._private = _private_callable
        mock_obj._private2 = public_callable
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(result, [])

    def _unregister_opts(self):
        CONF.reset()
        category_opt = cfg.SubCommandOpt("category",
                                         title="Command categories",
                                         help="Available categories"
                                         )
        CONF.unregister_opt(category_opt)

    @mock.patch("oslo.config.cfg.CONF",
                side_effect=cfg.ConfigFilesNotFoundError("config_file"))
    @mock.patch("rally.cmd.cliutils.CONF", config_file=None)
    def test_run_fails(self, mock_cmd_cliutils_conf, mock_cliutils_conf):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "show", "flavors"], categories)
        self.assertEqual(ret, 2)

    def test_run_version(self):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "version"], categories)
        self.assertEqual(ret, 0)

    def test_run_bash_completion(self):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "bash-completion"], categories)
        self.assertEqual(ret, 0)

    def test_run_bash_completion_with_query_category(self):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "bash-completion", "info"], categories)
        self.assertEqual(ret, 0)

    def test_run_show(self):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "show", "keypairs"], categories)
        self.assertEqual(ret, 1)

    @mock.patch("rally.openstack.common.cliutils.validate_args",
                side_effect=exceptions.MissingArgs("missing"))
    def test_run_show_fails(self, mock_validate_args):
        categories = {
                    "deployment": deployment.DeploymentCommands,
                    "info": info.InfoCommands,
                    "show": show.ShowCommands,
                    "task": task.TaskCommands,
                    "use": use.UseCommands,
                    "verify": verify.VerifyCommands}
        ret = cliutils.run(["rally", "show", "keypairs"], categories)
        self.assertTrue(mock_validate_args.called)
        self.assertEqual(ret, 1)

    def test_run_failed_to_open_file(self):

        class FailuresCommands(object):

            def failed_to_open_file(self):
                raise IOError("No such file")

        ret = cliutils.run(["rally", "failure", "failed_to_open_file"],
                           {"failure": FailuresCommands})
        self.assertEqual(1, ret)
