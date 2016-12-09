# Copyright 2014: Mirantis Inc.
# Copyright 2014: Catalyst IT Ltd.
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

import copy
import json
import os
import re
import traceback
import unittest

import six

from rally import api
from rally.common import db
from rally.common import objects
from rally import plugins
from rally.plugins.openstack.context.keystone import users
from tests.functional import utils


class TestTaskSamples(unittest.TestCase):

    def _skip(self, validation_output):
        """Help to decide do we want to skip this result or not.

        :param validation_output: string representation of the
        error that we want to check
        :return: True if we want to skip this error
        of task sample validation, otherwise False.
        """

        skip_lst = ["[Ss]ervice is not available",
                    "is not installed. To install it run",
                    "extension.* is not configured"]
        for check_str in skip_lst:
            if re.search(check_str, validation_output) is not None:
                return True
        return False

    @plugins.ensure_plugins_are_loaded
    def test_task_samples_is_valid(self):
        rally = utils.Rally(force_new_db=True)
        # In TestTaskSamples, Rally API will be called directly (not via
        # subprocess), so we need to change database options to temp database.
        db.db_options.set_defaults(
            db.CONF, connection="sqlite:///%s/db" % rally.tmp_dir)

        # let's use pre-created users to make TestTaskSamples quicker
        deployment = api.Deployment.get("MAIN")
        admin_cred = objects.Credential(**deployment["admin"])

        ctx = {"admin": {"credential": admin_cred},
               "task": {"uuid": self.__class__.__name__}}
        user_ctx = users.UserGenerator(ctx)
        user_ctx.setup()
        self.addCleanup(user_ctx.cleanup)

        config = deployment["config"]
        user = copy.copy(config["admin"])
        user["username"] = ctx["users"][0]["credential"].username
        user["password"] = ctx["users"][0]["credential"].password
        if "project_name" in config["admin"]:
            # it is Keystone
            user["project_name"] = ctx["users"][0]["credential"].tenant_name
        else:
            user["tenant_name"] = ctx["users"][0]["credential"].tenant_name
        config["users"] = [user]

        rally("deployment destroy MAIN", write_report=False)
        deployment_cfg = os.path.join(rally.tmp_dir, "new_deployment.json")
        with open(deployment_cfg, "w") as f:
            f.write(json.dumps(config))
        rally("deployment create --name MAIN --filename %s" % deployment_cfg,
              write_report=False)

        samples_path = os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir,
            "samples", "tasks")
        matcher = re.compile("\.json$")

        for dirname, dirnames, filenames in os.walk(samples_path):
            # NOTE(rvasilets): Skip by suggest of boris-42 because in
            # future we don't what to maintain this dir
            if dirname.find("tempest-do-not-run-against-production") != -1:
                continue
            for filename in filenames:
                full_path = os.path.join(dirname, filename)

                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if not matcher.search(filename):
                    continue
                with open(full_path) as task_file:
                    try:
                        input_task = task_file.read()
                        rendered_task = api.Task.render_template(input_task)
                        task_config = json.loads(rendered_task)
                        api.Task.validate("MAIN", task_config)
                    except Exception as e:
                        if not self._skip(six.text_type(e)):
                            print(traceback.format_exc())
                            print("Failed on task config %s with error." %
                                  full_path)
                            raise
