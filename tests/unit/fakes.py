# Copyright 2013: Mirantis Inc.
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

import itertools
import multiprocessing
from unittest import mock

from rally import api
from rally.common import utils as rally_utils
from rally import consts
from rally.task import context
from rally.task import scenario


class FakeScenario(scenario.Scenario):

    def idle_time(self):
        return 0

    def do_it(self, **kwargs):
        pass

    def with_output(self, **kwargs):
        return {"data": {"a": 1}, "error": None}

    def with_add_output(self):
        self.add_output(additive={"title": "Additive",
                                  "description": "Additive description",
                                  "data": [["a", 1]],
                                  "chart_plugin": "FooPlugin"},
                        complete={"title": "Complete",
                                  "description": "Complete description",
                                  "data": [["a", [[1, 2], [2, 3]]]],
                                  "chart_plugin": "BarPlugin"})

    def too_long(self, **kwargs):
        pass

    def something_went_wrong(self, **kwargs):
        raise Exception("Something went wrong")

    def raise_timeout(self, **kwargs):
        raise multiprocessing.TimeoutError()


@scenario.configure(name="classbased.fooscenario")
class FakeClassBasedScenario(FakeScenario):
    """Fake class-based scenario."""

    def run(self, *args, **kwargs):
        pass


class FakeTimer(rally_utils.Timer):

    def duration(self):
        return 10

    def timestamp(self):
        return 0

    def finish_timestamp(self):
        return 3


@context.configure(name="fake", order=1)
class FakeContext(context.Context):

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "test": {
                "type": "integer"
            },
        },
        "additionalProperties": False
    }

    def __init__(self, context_obj=None):
        context_obj = context_obj or {}
        context_obj.setdefault("config", {})
        context_obj["config"].setdefault("fake", None)
        context_obj.setdefault("task", mock.MagicMock())
        super(FakeContext, self).__init__(context_obj)

    def setup(self):
        pass

    def cleanup(self):
        pass


class FakeDeployment(dict):

    def __init__(self, **kwargs):
        platform = kwargs.pop("platform", "openstack")
        kwargs["credentials"] = {
            platform: [{"admin": kwargs.pop("admin", None),
                        "users": kwargs.pop("users", [])}],
            "default": [{"admin": None, "users": []}]}
        dict.__init__(self, **kwargs)
        self.update_status = mock.Mock()
        self.env_obj = mock.Mock()

    def get_platforms(self):
        return [platform for platform in self["credentials"]]

    def get_credentials_for(self, platform):
        return self["credentials"][platform][0]

    def verify_connections(self):
        pass

    def get_validation_context(self):
        return {}


class FakeTask(dict, object):

    def __init__(self, task=None, temporary=False, **kwargs):
        self.is_temporary = temporary
        self.update_status = mock.Mock()
        self.set_failed = mock.Mock()
        self.set_validation_failed = mock.Mock()
        task = task or {}
        for k, v in itertools.chain(task.items(), kwargs.items()):
            self[k] = v
        self.task = self

    def to_dict(self):
        return self


class FakeAPI(object):

    def __init__(self):
        self._deployment = mock.create_autospec(api._Deployment)
        self._task = mock.create_autospec(api._Task)
        self._verifier = mock.create_autospec(api._Verifier)
        self._verification = mock.create_autospec(api._Verification)

    @property
    def deployment(self):
        return self._deployment

    @property
    def task(self):
        return self._task

    @property
    def verifier(self):
        return self._verifier

    @property
    def verification(self):
        return self._verification
