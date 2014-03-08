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

import abc


from oslo.config import cfg

from rally.benchmark.context import cleaner as cleaner_ctx
from rally.benchmark.context import secgroup as secgroup_ctx
from rally.benchmark.context import users as users_ctx
from rally.benchmark.scenarios import base
from rally.benchmark import utils
from rally.openstack.common import log as logging
from rally import osclients
from rally import utils as rutils


LOG = logging.getLogger(__name__)


def _run_scenario_once(args):
    i, cls, method_name, admin, user, kwargs = args

    LOG.info("ITER: %s START" % i)

    # TODO(boris-42): remove context
    scenario = cls(
            context={},
            admin_clients=osclients.Clients(admin["endpoint"]),
            clients=osclients.Clients(user["endpoint"]))

    try:
        scenario_output = None
        with rutils.Timer() as timer:
            scenario_output = getattr(scenario, method_name)(**kwargs)
        error = None
    except Exception as e:
        error = utils.format_exc(e)
        if cfg.CONF.debug:
            LOG.exception(e)
    finally:
        status = "Error %s: %s" % tuple(error[0:2]) if error else "OK"
        LOG.info("ITER: %(i)s END: %(status)s" % {"i": i, "status": status})

        return {"time": timer.duration() - scenario.idle_time(),
                "idle_time": scenario.idle_time(),
                "error": error,
                "scenario_output": scenario_output,
                "atomic_actions_time": scenario.atomic_actions_time()}


class ScenarioRunner(object):
    """Base class for all scenario runners.

    Scenario runner is an entity that implements a certain strategy of
    launching benchmark scenarios, e.g. running them continuously or
    periodically for a given number of times or seconds.
    These strategies should be implemented in subclasses of ScenarioRunner
    in the_run_scenario() method.
    """

    def __init__(self, task, endpoints):
        base.Scenario.register()

        self.task = task
        self.endpoints = endpoints
        # NOTE(msdubov): Passing predefined user endpoints hasn't been
        #                implemented yet, so the scenario runner always gets
        #                a single admin endpoint here.
        self.admin_user = endpoints[0]
        self.users = []

    @staticmethod
    def get_runner(task, endpoint, config):
        """Returns instance of a scenario runner for execution type."""
        execution_type = config.get('execution', 'continuous')
        for runner in rutils.itersubclasses(ScenarioRunner):
            if execution_type == runner.__execution_type__:
                new_runner = runner(task, endpoint)
                return new_runner

    @abc.abstractmethod
    def _run_scenario(self, cls, method_name, context, args, config):
        """Runs the specified benchmark scenario with given arguments.

        :param cls: The Scenario class where the scenario is implemented
        :param method_name: Name of the method that implements the scenario
        :param context: Benchmark context that contains users, admin & other
                        information, that was created before benchmark started.
        :param args: Arguments to call the scenario method with
        :param config: Configuration dictionary that contains strategy-specific
                       parameters like the number of times to run the scenario

        :returns: List of results fore each single scenario iteration,
                  where each result is a dictionary
        """

    def _prepare_and_run_scenario(self, context, name, kwargs):
        cls_name, method_name = name.split(".")
        cls = base.Scenario.get_by_name(cls_name)

        args = kwargs.get('args', {})
        config = kwargs.get('config', {})

        with secgroup_ctx.AllowSSH(context) as allow_ssh:
            allow_ssh.setup()
            return self._run_scenario(cls, method_name, context, args, config)

    def _run_as_admin(self, name, kwargs):
        config = kwargs.get('config', {})

        context = {
            "task": self.task,
            "admin": {"endpoint": self.admin_user},
            "config": {
                "users": {
                    "tenants": config.get("tenants", 1),
                    "users_per_tenant": config.get("users_per_tenant", 1)
                }
            }
        }

        with users_ctx.UserGenerator(context) as generator:
            generator.setup()
            with cleaner_ctx.ResourceCleaner(context) as cleaner:
                cleaner.setup()
                return self._prepare_and_run_scenario(context, name, kwargs)

    def _run_as_non_admin(self, name, kwargs):
        # TODO(boris-42): It makes sense to use UserGenerator here as well
        #                 take a look at comment in UserGenerator.__init__()
        context = {}
        with cleaner_ctx.ResourceCleaner(context):
            return self._prepare_and_run_scenario(context, name, kwargs)

    def run(self, name, kwargs):
        if self.admin_user:
            return self._run_as_admin(name, kwargs)
        else:
            return self._run_as_non_admin(name, kwargs)
