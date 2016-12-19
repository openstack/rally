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

import re
import time

import jinja2
import jinja2.meta
import jsonschema

from rally.common.i18n import _, _LI, _LE
from rally.common import logging
from rally.common import objects
from rally import consts
from rally.deployment import engine as deploy_engine
from rally import exceptions
from rally import osclients
from rally.task import engine

LOG = logging.getLogger(__name__)


class Deployment(object):

    @classmethod
    def create(cls, config, name):
        """Create a deployment.

        :param config: a dict with deployment configuration
        :param name: a str represents a name of the deployment
        :returns: Deployment object
        """

        try:
            deployment = objects.Deployment(name=name, config=config)
        except exceptions.DeploymentNameExists as e:
            if logging.is_debug():
                LOG.exception(e)
            raise

        deployer = deploy_engine.Engine.get_engine(
            deployment["config"]["type"], deployment)
        try:
            deployer.validate()
        except jsonschema.ValidationError:
            LOG.error(_LE("Deployment %s: Schema validation error.") %
                      deployment["uuid"])
            deployment.update_status(consts.DeployStatus.DEPLOY_FAILED)
            raise

        with deployer:
            credentials = deployer.make_deploy()
            deployment.update_credentials(credentials)
            return deployment

    @classmethod
    def destroy(cls, deployment):
        """Destroy the deployment.

        :param deployment: UUID or name of the deployment
        """
        # TODO(akscram): We have to be sure that there are no running
        #                tasks for this deployment.
        # TODO(akscram): Check that the deployment have got a status that
        #                is equal to "*->finished" or "deploy->inconsistent".
        deployment = objects.Deployment.get(deployment)
        try:
            deployer = deploy_engine.Engine.get_engine(
                deployment["config"]["type"], deployment)
            with deployer:
                deployer.make_cleanup()
        except exceptions.PluginNotFound:
            LOG.info(_("Deployment %s will be deleted despite"
                       " exception") % deployment["uuid"])

        deployment.delete()

    @classmethod
    def recreate(cls, deployment):
        """Performs a cleanup and then makes a deployment again.

        :param deployment: UUID or name of the deployment
        """
        deployment = objects.Deployment.get(deployment)
        deployer = deploy_engine.Engine.get_engine(
            deployment["config"]["type"], deployment)
        with deployer:
            deployer.make_cleanup()
            credentials = deployer.make_deploy()
            deployment.update_credentials(credentials)

    @classmethod
    def get(cls, deployment):
        """Get the deployment.

        :param deployment: UUID or name of the deployment
        :returns: Deployment instance
        """
        return objects.Deployment.get(deployment)

    @classmethod
    def service_list(cls, deployment):
        """Get the services list.

        :param deployment: Deployment object
        :returns: Service list
        """
        # TODO(kun): put this work into objects.Deployment
        clients = osclients.Clients(objects.Credential(**deployment["admin"]))
        return clients.services()

    @staticmethod
    def list(status=None, parent_uuid=None, name=None):
        """Get the deployments list.

        :returns: Deployment list
        """
        return objects.Deployment.list(status, parent_uuid, name)

    @classmethod
    def check(cls, deployment):
        """Check keystone authentication and list all available services.

        :returns: Service list
        """
        services = cls.service_list(deployment)
        users = deployment["users"]
        for endpoint_dict in users:
            osclients.Clients(objects.Credential(**endpoint_dict)).keystone()

        return services


class Task(object):

    TASK_RESULT_SCHEMA = objects.task.TASK_RESULT_SCHEMA

    @staticmethod
    def list(**filters):
        return objects.Task.list(**filters)

    @staticmethod
    def get(task_id):
        return objects.Task.get(task_id)

    @staticmethod
    def get_detailed(task_id, extended_results=False):
        """Get detailed task data.

        :param task_id: str task UUID
        :param extended_results: whether to return task data as dict
                                 with extended results
        :returns: rally.common.db.sqlalchemy.models.Task
        :returns: dict
        """
        task = objects.Task.get_detailed(task_id)
        if task and extended_results:
            task = dict(task)
            task["results"] = objects.Task.extend_results(task["results"])
        return task

    @classmethod
    def render_template(cls, task_template, template_dir="./", **kwargs):
        """Render jinja2 task template to Rally input task.

        :param task_template: String that contains template
        :param template_dir: The path of directory contain template files
        :param kwargs: Dict with template arguments
        :returns: rendered template str
        """

        def is_really_missing(mis, task_template):
            # NOTE(boris-42): Removing variables that have default values from
            #                 missing. Construction that won't be properly
            #                 checked is {% set x = x or 1}
            if re.search(mis.join(["{%\s*set\s+", "\s*=\s*", "[^\w]+"]),
                         task_template):
                return False
            # NOTE(jlk): Also check for a default filter which can show up as
            #            a missing variable
            if re.search(mis + "\s*\|\s*default\(", task_template):
                return False
            return True

        # NOTE(boris-42): We have to import builtins to get the full list of
        #                 builtin functions (e.g. range()). Unfortunately,
        #                 __builtins__ doesn't return them (when it is not
        #                 main module)
        from six.moves import builtins

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir, encoding="utf8"))
        env.globals.update(cls.create_template_functions())
        ast = env.parse(task_template)
        # NOTE(Julia Varigina):
        # Bug in jinja2.meta.find_undeclared_variables
        #
        # The method shows inconsistent behavior:
        # it does not return undeclared variables that appear
        # in included templates only (via {%- include "some_template.yaml"-%})
        # and in the same time is declared in jinja2.Environment.globals.
        #
        # This is different for undeclared variables that appear directly
        # in task_template. The method jinja2.meta.find_undeclared_variables
        # returns an undeclared variable that is used in task_template
        # and is set in jinja2.Environment.globals.
        #
        # Despite this bug, jinja resolves values
        # declared in jinja2.Environment.globals for both types of undeclared
        # variables and successfully renders templates in both cases.
        required_kwargs = jinja2.meta.find_undeclared_variables(ast)
        missing = (set(required_kwargs) - set(kwargs) - set(dir(builtins)) -
                   set(env.globals))
        real_missing = [mis for mis in missing
                        if is_really_missing(mis, task_template)]
        if real_missing:
            multi_msg = _("Please specify next template task arguments: %s")
            single_msg = _("Please specify template task argument: %s")

            raise TypeError((len(real_missing) > 1 and multi_msg or single_msg)
                            % ", ".join(real_missing))

        return env.from_string(task_template).render(**kwargs)

    @classmethod
    def create_template_functions(cls):

        def template_min(int1, int2):
            return min(int1, int2)

        def template_max(int1, int2):
            return max(int1, int2)

        def template_round(float1):
            return int(round(float1))

        def template_ceil(float1):
            import math
            return int(math.ceil(float1))

        return {"min": template_min, "max": template_max,
                "ceil": template_ceil, "round": template_round}

    @classmethod
    def create(cls, deployment, tag):
        """Create a task without starting it.

        Task is a list of benchmarks that will be called one by one, results of
        execution will be stored in DB.

        :param deployment: UUID or name of the deployment
        :param tag: tag for this task
        :returns: Task object
        """

        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        return objects.Task(deployment_uuid=deployment_uuid, tag=tag)

    @classmethod
    def validate(cls, deployment, config, task_instance=None):
        """Validate a task config against specified deployment.

        :param deployment: UUID or name of the deployment
        :param config: a dict with a task configuration
        """
        deployment = objects.Deployment.get(deployment)
        task = task_instance or objects.Task(
            deployment_uuid=deployment["uuid"], temporary=True)
        benchmark_engine = engine.TaskEngine(
            config, task, admin=deployment["admin"], users=deployment["users"])

        benchmark_engine.validate()

    @classmethod
    def start(cls, deployment, config, task=None, abort_on_sla_failure=False):
        """Start a task.

        Task is a list of benchmarks that will be called one by one, results of
        execution will be stored in DB.

        :param deployment: UUID or name of the deployment
        :param config: a dict with a task configuration
        :param task: Task object. If None, it will be created
        :param abort_on_sla_failure: If set to True, the task execution will
                                     stop when any SLA check for it fails
        """
        deployment = objects.Deployment.get(deployment)
        task = task or objects.Task(deployment_uuid=deployment["uuid"])

        if task.is_temporary:
            raise ValueError(_(
                "Unable to run a temporary task. Please check your code."))

        LOG.info("Benchmark Task %s on Deployment %s" % (task["uuid"],
                                                         deployment["uuid"]))
        benchmark_engine = engine.TaskEngine(
            config, task, admin=deployment["admin"], users=deployment["users"],
            abort_on_sla_failure=abort_on_sla_failure)

        try:
            benchmark_engine.run()
        except Exception:
            deployment.update_status(consts.DeployStatus.DEPLOY_INCONSISTENT)
            raise

    @classmethod
    def abort(cls, task_uuid, soft=False, async=True):
        """Abort running task.

        :param task_uuid: The UUID of the task
        :type task_uuid: str
        :param soft: If set to True, task should be aborted after execution of
                     current scenario, otherwise as soon as possible before
                     all the scenario iterations finish [Default: False]
        :type soft: bool
        :param async: don't wait until task became in 'running' state
                      [Default: False]
        :type async: bool
        """

        if not async:
            current_status = objects.Task.get_status(task_uuid)
            if current_status in objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT:
                LOG.info(_LI("Task status is '%s'. Should wait until it became"
                             " 'running'") % current_status)
                while (current_status in
                       objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT):
                    time.sleep(1)
                    current_status = objects.Task.get_status(task_uuid)

        objects.Task.get(task_uuid).abort(soft=soft)

        if not async:
            LOG.info(_LI("Waiting until the task stops."))
            finished_stages = [consts.TaskStatus.ABORTED,
                               consts.TaskStatus.FINISHED,
                               consts.TaskStatus.FAILED]
            while objects.Task.get_status(task_uuid) not in finished_stages:
                time.sleep(1)

    @classmethod
    def delete(cls, task_uuid, force=False):
        """Delete the task.

        :param task_uuid: The UUID of the task
        :param force: If set to True, then delete the task despite to the
                      status
        :raises TaskInvalidStatus: when the status of the task is not
                                   in FINISHED, FAILED or ABORTED and
                                   the force argument is not True
        """
        if force:
            objects.Task.delete_by_uuid(task_uuid, status=None)
        elif objects.Task.get_status(task_uuid) in (
                consts.TaskStatus.ABORTED,
                consts.TaskStatus.FINISHED,
                consts.TaskStatus.FAILED):
            objects.Task.delete_by_uuid(task_uuid, status=None)
        else:
            objects.Task.delete_by_uuid(
                task_uuid, status=consts.TaskStatus.FINISHED)
