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
from oslo_config import cfg
import testtools

from rally.cmd import cliutils
from rally.cmd.commands import deployment
from rally.cmd.commands import info
from rally.cmd.commands import show
from rally.cmd.commands import task
from rally.cmd.commands import use
from rally.cmd.commands import verify
from rally import exceptions
from rally.openstack.common import cliutils as common_cliutils
from tests.unit import test

CONF = cfg.CONF

FAKE_TASK_UUID = "bb0f621c-29bd-495c-9d7a-d844335ed0fa"


@testtools.skip(
    "These tests are not work with latest(1.6.0) oslo.config (see "
    "https://review.openstack.org/#/c/135150 for more details). "
    "Should wait for new release of oslo.config with appropriate fix.")
class CliUtilsTestCase(test.TestCase):

    def setUp(self):
        super(CliUtilsTestCase, self).setUp()
        self.categories = {
            "deployment": deployment.DeploymentCommands,
            "info": info.InfoCommands,
            "show": show.ShowCommands,
            "task": task.TaskCommands,
            "use": use.UseCommands,
            "verify": verify.VerifyCommands
        }

    def tearDown(self):
        self._unregister_opts()
        super(CliUtilsTestCase, self).tearDown()

    def test_make_header(self):
        h1 = cliutils.make_header("msg", size="4", symbol="=")
        self.assertEqual(h1, "====\n msg\n====\n")

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

    def test__methods_of_with_class(self):
        class fake_class(object):
            def public(self):
                pass

            def _private(self):
                pass
        result = cliutils._methods_of(fake_class)
        self.assertEqual(1, len(result))
        self.assertEqual("public", result[0][0])

    def test__methods_of_with_object(self):
        class fake_class(object):
            def public(self):
                pass

            def _private(self):
                pass
        mock_obj = fake_class()
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(1, len(result))
        self.assertEqual("public", result[0][0])

    def test__methods_of_empty_result(self):
        class fake_class(object):
            def _private(self):
                pass

            def _private2(self):
                pass
        mock_obj = fake_class()
        result = cliutils._methods_of(mock_obj)
        self.assertEqual(result, [])

    def _unregister_opts(self):
        CONF.reset()
        category_opt = cfg.SubCommandOpt("category",
                                         title="Command categories",
                                         help="Available categories"
                                         )
        CONF.unregister_opt(category_opt)

    @mock.patch("rally.cmd.cliutils.CONF", config_file=None,
                side_effect=cfg.ConfigFilesNotFoundError("config_file"))
    def test_run_fails(self, mock_cmd_cliutils_conf):
        ret = cliutils.run(["rally", "show", "flavors"], self.categories)
        self.assertEqual(ret, 2)

    def test_run_version(self):
        ret = cliutils.run(["rally", "version"], self.categories)
        self.assertEqual(ret, 0)

    def test_run_bash_completion(self):
        ret = cliutils.run(["rally", "bash-completion"], self.categories)
        self.assertEqual(ret, 0)

    def test_run_bash_completion_with_query_category(self):
        ret = cliutils.run(["rally", "bash-completion", "info"],
                           self.categories)
        self.assertEqual(ret, 0)

    def test_run_show(self):
        ret = cliutils.run(["rally", "show", "keypairs"], self.categories)
        self.assertEqual(ret, 1)

    @mock.patch("rally.db.task_get",
                side_effect=exceptions.TaskNotFound(FAKE_TASK_UUID))
    def test_run_task_not_found(self, mock_task_get):
        ret = cliutils.run(["rally", "task", "status", "%s" % FAKE_TASK_UUID],
                           self.categories)
        self.assertTrue(mock_task_get.called)
        self.assertEqual(ret, 1)

    @mock.patch("rally.openstack.common.cliutils.validate_args",
                side_effect=common_cliutils.MissingArgs("missing"))
    def test_run_show_fails(self, mock_validate_args):
        ret = cliutils.run(["rally", "show", "keypairs"], self.categories)
        self.assertTrue(mock_validate_args.called)
        self.assertEqual(ret, 1)

    def test_run_failed_to_open_file(self):

        class FailuresCommands(object):

            def failed_to_open_file(self):
                raise IOError("No such file")

        ret = cliutils.run(["rally", "failure", "failed_to_open_file"],
                           {"failure": FailuresCommands})
        self.assertEqual(1, ret)
