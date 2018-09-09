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

import collections
import json
import os
import re
import sys
import time

import jinja2
import jinja2.meta
import requests
from requests.packages import urllib3

from rally.common import cfg
from rally.common import logging
from rally.common import objects
from rally.common import opts
from rally.common.plugin import discover
from rally.common import utils
from rally.common import version as rally_version
from rally import consts
from rally import exceptions
from rally.task import engine
from rally.task import exporter as texporter
from rally.task import task_cfg
from rally.verification import context as vcontext
from rally.verification import manager as vmanager
from rally.verification import reporter as vreporter


CONF = cfg.CONF
LOG = logging.getLogger(__name__)
API_REQUEST_PREFIX = "/api"


opts.register()


class APIGroup(object):
    def __init__(self, api):
        """Initialize API group.

        :param api: an instance of rally.api.API object
        """
        self.api = api


class _Deployment(APIGroup):

    def _create(self, config, name):
        """Create a deployment.

        :param config: a dict with deployment configuration
        :param name: a str represents a name of the deployment
        :returns: Deployment object
        """

        # NOTE(andreykurilin): the following transformation is a preparatory
        #   step for further refactoring (it will be done soon).
        print_warning = False

        extras = {}
        if "type" in config:
            if config["type"] != "ExistingCloud":
                raise exceptions.RallyException(
                    "You are using deployment type which doesn't exist. Please"
                    " check the latest documentation and fix deployment "
                    "config.")

            config = config["creds"]
            extras = config.get("extra", {})
            print_warning = True

        try:
            deployment = objects.Deployment(name=name, config=config,
                                            extras=extras)
        except exceptions.DBRecordExists:
            if logging.is_debug():
                LOG.exception("Deployment with such name exists")
            raise

        if print_warning:
            new_conf = deployment.env_obj.spec
            LOG.warning(
                "The used config schema is deprecated since Rally 0.10.0. "
                "The new one is much simpler, try it now:\n%s"
                % json.dumps(new_conf, indent=4)
            )

        return deployment

    def create(self, config, name):
        return self._create(config, name).to_dict()

    def destroy(self, deployment):
        """Destroy the deployment.

        :param deployment: UUID or name of the deployment
        """

        deploy = objects.Deployment.get(deployment)

        deploy.env_obj.destroy(skip_cleanup=True)
        deploy.env_obj.delete()

    def recreate(self, deployment, config=None):
        """Performs a cleanup and then makes a deployment again.

        :param deployment: UUID or name of the deployment
        :param config: an optional dict with deployment config to update before
                       redeploy
        """
        raise exceptions.RallyException("Sorry, but recreate method of "
                                        "deployments is temporary disabled.")

    def _get(self, deployment):
        """Get the deployment.

        :param deployment: UUID or name of the deployment
        :returns: Deployment instance
        """
        return objects.Deployment.get(deployment)

    def get(self, deployment):
        return self._get(deployment).to_dict()

    def list(self, status=None, parent_uuid=None, name=None):
        """Get the deployments list.

        :returns: Deployment list
        """
        return [deployment.to_dict() for deployment in
                objects.Deployment.list(status, parent_uuid, name)]

    def check(self, deployment):
        """Check keystone authentication and list all available services.

        :param deployment: UUID of deployment
        :returns: Service list
        """
        env = self._get(deployment).env_obj

        result = {}

        for p, res in env.check_health().items():
            name = "openstack" if p == "existing@openstack" else p
            if not res["available"]:
                # NOTE(andreykurilin): the old behavior supports 2 keys
                #   for storing errors: admin_error and user_error.
                #   Since admin/users is not mandatory thing for new design
                #   of Platforms, let's put platform error to "admin_error"
                key = "admin_error"
                if name == "openstack":
                    if res["message"].startswith("Bad user creds"):
                        key = "user_error"

                if "traceback" in res:
                    # NOTE(andreykurilin): the last not null line in traceback
                    #   includes Exception cls with a message. By parsing it,
                    #   we can get etype.
                    trace = res["traceback"].split("\n")
                    last_line = [l for l in trace if l][-1]
                    etype, _msg = last_line.split(":", 1)
                else:
                    etype = "n/a"
                result[name] = [
                    {
                        key: {
                            "etype": etype,
                            "msg": res["message"],
                            "trace": res.get("traceback", "n/a")
                        },
                        "services": []
                    }
                ]
            else:
                if name == "openstack":
                    services = env.get_info()[p]["info"]["services"]
                    # backward compatibility
                    for s in services:
                        if "name" not in s:
                            s["name"] = "__unknown__"

                    result[name] = [{"services": services}]
                else:
                    # NOTE(andreykurilin): the info method of platforms allows
                    #   to return whatever single platform wants, i.e
                    #   Platform X can return just a version and no services
                    #   at all. Checking for 'services' key there is not a
                    #   solution, since the value of it can have the format
                    #   which differs from openstack-like (the old design of
                    #   Deployment component)
                    result[name] = [{"services": []}]

        return result


class _Task(APIGroup):

    TASK_SCHEMA = objects.task.TASK_SCHEMA

    def list(self, **filters):
        return [task.to_dict() for task in objects.Task.list(**filters)]

    def get(self, task_id, detailed=False):
        """Get task data

        :param task_id: Task UUID
        :param detailed: whether return detailed information(including
            subtasks and workloads) or not.
        """
        return objects.Task.get(task_id, detailed=detailed).to_dict()

    # TODO(andreykurilin): move it to some kind of utils
    def render_template(self, task_template, template_dir="./", **kwargs):
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
        env.globals.update(self.create_template_functions())
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
            multi_msg = "Please specify next template task arguments: %s"
            single_msg = "Please specify template task argument: %s"

            raise TypeError((len(real_missing) > 1 and multi_msg or single_msg)
                            % ", ".join(real_missing))

        render_template = env.from_string(task_template).render(**kwargs)
        return render_template

    def create_template_functions(self):

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

    def create(self, deployment, tags=None):
        """Create a task without starting it.

        Task is a list of subtasks that are called one by one, results of
        execution are stored into DB.

        Every subtask is sort of test case which is created by combination
        of scenario, runner, contexts, sla and hoooks plugins.

        :param deployment: UUID or name of the deployment
        :param tags: a list of tags for this task
        :returns: Task object
        """
        deployment = objects.Deployment.get(deployment)
        if deployment["status"] != consts.DeployStatus.DEPLOY_FINISHED:
            raise exceptions.DeploymentNotFinishedStatus(
                name=deployment["name"],
                uuid=deployment["uuid"],
                status=deployment["status"])

        return objects.Task(env_uuid=deployment["uuid"],
                            tags=tags).to_dict()

    def validate(self, deployment, config, task_instance=None, task=None):
        """Validate a task config against specified deployment.

        :param deployment: UUID or name of the deployment (will be ignored in
            case of transmitting task_instance or task arguments)
        :param config: a dict with a task configuration
        :param task_instance: DEPRECATED. Use "task" argument to transmit task
            uuid instead
        """
        if task_instance is not None:
            LOG.warning("Transmitting task object in `task validate` is "
                        "deprecated since Rally 0.10. To use pre-created "
                        "task, transmit task UUID instead via `task` "
                        "argument.")
            task = objects.Task.get(task_instance["uuid"])
            deployment = task["deployment_uuid"]
        elif task:
            task = objects.Task.get(task)
            deployment = task["deployment_uuid"]
        else:
            task = objects.Task(env_uuid=deployment, temporary=True)
        deployment = objects.Deployment.get(deployment)

        try:
            config = task_cfg.TaskConfig(config)
        except exceptions.InvalidTaskException:
            # it is a proper formed exception, nothing to do
            raise
        except Exception as e:
            if logging.is_debug():
                LOG.exception("Unexpected error had happened")
            raise exceptions.InvalidTaskException(str(e))

        engine.TaskEngine(config, task, deployment.env_obj).validate()

    def start(self, deployment, config, task=None, abort_on_sla_failure=False):
        """Validate and start a task.

        Task is a list of subtasks that are called one by one, results of
        execution are stored in DB.

        :param deployment: UUID or name of the deployment (will be ignored in
            case of transmitting existing task)
        :param config: a dict with a task configuration
        :param task: Task UUID to use pre-created task. If None, new task will
            be created
        :param abort_on_sla_failure: If set to True, the task execution is
                                     stop when any of SLA checks fails
        """
        if task and isinstance(task, objects.Task):
            LOG.warning("Transmitting task object in `task start` is "
                        "deprecated since Rally 0.10. To use pre-created "
                        "task, transmit task UUID instead.")
            if task.is_temporary:
                raise ValueError(
                    "Unable to run a temporary task. Please check your code.")
            task = objects.Task.get(task["uuid"])
        elif task is not None:
            task = objects.Task.get(task)

        if task is not None:
            deployment = task["deployment_uuid"]

        deployment = objects.Deployment.get(deployment)
        if deployment["status"] != consts.DeployStatus.DEPLOY_FINISHED:
            raise exceptions.DeploymentNotFinishedStatus(
                name=deployment["name"],
                uuid=deployment["uuid"],
                status=deployment["status"])

        try:
            config = task_cfg.TaskConfig(config)
        except exceptions.InvalidTaskException:
            # it is a proper formed exception, nothing to do
            raise
        except Exception as e:
            if logging.is_debug():
                LOG.exception("Unexpected error had happened")
            raise exceptions.InvalidTaskException(str(e))

        if task is None:
            task = objects.Task(deployment_uuid=deployment["uuid"],
                                title=config.title,
                                description=config.description)

        task_engine = engine.TaskEngine(
            config, task, deployment.env_obj,
            abort_on_sla_failure=abort_on_sla_failure)

        task_engine.validate()

        LOG.info("Task %s input file is valid." % task["uuid"])
        LOG.info("Run Task %s against Deployment %s"
                 % (task["uuid"], deployment["uuid"]))

        task_engine.run()

        return task["uuid"], task.get_status(task["uuid"])

    def abort(self, task_uuid, soft=False, wait=False, **kwargs):
        """Abort running task.

        :param task_uuid: The UUID of the task
        :type task_uuid: str
        :param soft: If set to True, task should be aborted after execution of
                     current scenario, otherwise as soon as possible before
                     all the scenario iterations finish [Default: False]
        :type soft: bool
        :param wait: wait until task stops [Default: False]
        :type wait: bool
        """
        if kwargs:
            if len(kwargs) != 1 or "async" not in kwargs:
                raise TypeError("API method task.abort accept only one "
                                "argument 'async' (which is deprecated in "
                                "favor of 'wait').")
            elif "async" in kwargs:
                LOG.warning("The argument 'async' of API method task.abort is "
                            "deprecated since Rally 1.1.0 in favor of new "
                            "argument 'wait' which doesn't conflict with a "
                            "reserved keywords in python 3.7")
                wait = not kwargs["async"]

        if wait:
            current_status = objects.Task.get_status(task_uuid)
            if current_status in objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT:
                LOG.info(
                    "Task status is '%s' waiting until it became 'running'"
                    % current_status)
                while (current_status in
                       objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT):
                    time.sleep(1)
                    current_status = objects.Task.get_status(task_uuid)

        objects.Task.get(task_uuid).abort(soft=soft)

        if wait:
            LOG.info("Waiting until the task stops.")
            finished_stages = [consts.TaskStatus.ABORTED,
                               consts.TaskStatus.FINISHED,
                               consts.TaskStatus.CRASHED]
            while objects.Task.get_status(task_uuid) not in finished_stages:
                time.sleep(1)

    def delete(self, task_uuid, force=False):
        """Deletes all task data from database.

        :param task_uuid: The UUID of the task
        :param force: If set to True, then delete the task despite to the
                      status
        :raises DBConflict: when the status of the task is not
                            in FINISHED, FAILED or ABORTED and
                            the force argument is not True
        :raises DBRecordNotFound: when task doesn't exist
        """
        if force:
            objects.Task.delete_by_uuid(task_uuid, status=None)
        elif objects.Task.get_status(task_uuid) in (
                consts.TaskStatus.ABORTED,
                consts.TaskStatus.FINISHED,
                consts.TaskStatus.CRASHED):
            objects.Task.delete_by_uuid(task_uuid, status=None)
        else:
            objects.Task.delete_by_uuid(
                task_uuid, status=consts.TaskStatus.FINISHED)

    def import_results(self, deployment, task_results, tags=None):
        """Import json results of a task into rally database"""
        deployment = objects.Deployment.get(deployment)
        if deployment["status"] != consts.DeployStatus.DEPLOY_FINISHED:
            raise exceptions.DeploymentNotFinishedStatus(
                name=deployment["name"],
                uuid=deployment["uuid"],
                status=deployment["status"])

        task_inst = objects.Task(env_uuid=deployment["uuid"],
                                 tags=tags)
        task_inst.update_status(consts.TaskStatus.RUNNING)
        for subtask in task_results["subtasks"]:
            subtask_obj = task_inst.add_subtask(title=subtask.get("title"))
            for workload in subtask["workloads"]:
                for data in workload["data"]:
                    if not task_inst.result_has_valid_schema(data):
                        raise exceptions.RallyException(
                            "Task %s is trying to import "
                            "results in wrong format" % task_inst["uuid"])

                workload_obj = subtask_obj.add_workload(
                    name=workload["name"], description=workload["description"],
                    position=workload["position"], runner=workload["runner"],
                    runner_type=workload["runner_type"],
                    contexts=workload["contexts"], hooks=workload["hooks"],
                    sla=workload["sla"], args=workload["args"])

                chunk_size = CONF.raw_result_chunk_size
                workload_data_count = 0
                while len(workload["data"]) > chunk_size:
                    results_chunk = workload["data"][:chunk_size]
                    workload["data"] = workload["data"][chunk_size:]
                    results_chunk.sort(key=lambda x: x["timestamp"])
                    workload_obj.add_workload_data(workload_data_count,
                                                   {"raw": results_chunk})
                    workload_data_count += 1

                workload_obj.add_workload_data(workload_data_count,
                                               {"raw": workload["data"]})
                workload_obj.set_results(
                    sla_results=workload["sla_results"].get("sla"),
                    hooks_results=workload["hooks"],
                    start_time=workload["start_time"],
                    full_duration=workload["full_duration"],
                    load_duration=workload["load_duration"],
                    contexts_results=workload["contexts_results"])
            subtask_obj.update_status(consts.SubtaskStatus.FINISHED)
        task_inst.update_status(consts.SubtaskStatus.FINISHED)

        LOG.info("Task results have been successfully imported.")

        return task_inst.to_dict()

    def export(self, tasks, output_type, output_dest=None):
        """Generate a report for a task or a few tasks.

        :param tasks: List of tasks UUIDs or tasks results
        :param output_type: Plugin name of task exporter
        :param output_dest: Destination for task report
        """

        tasks_results = []
        tasks = tasks or []
        for task in tasks:
            if isinstance(task, dict):
                tasks_results.append(task)
            else:
                tasks_results.append(self.get(task_id=task, detailed=True))

        errors = texporter.TaskExporter.validate(
            output_type, context={}, config={},
            # wrap destination to a dict to allow extending options in future
            plugin_cfg={"destination": output_dest},
            vtype="syntax"
        )
        if errors:
            raise exceptions.ValidationError("\n".join(errors))

        reporter_cls = texporter.TaskExporter.get(output_type)

        LOG.info("Building '%s' report for the following task(s): '%s'."
                 % (output_type,
                    "', '".join([task["uuid"] for task in tasks_results])))
        result = texporter.TaskExporter.make(reporter_cls,
                                             tasks_results,
                                             output_dest,
                                             api=self.api)
        LOG.info("The report has been successfully built.")
        return result


class _Verifier(APIGroup):

    def list_plugins(self, platform=None):
        """List all plugins for verifiers management.

        :param platform: Verifier plugin platform
        """
        return [{"name": p.get_name(),
                 "platform": p.get_platform(),
                 "description": p.get_info()["title"],
                 "location": "%s.%s" % (p.__module__, p.__name__)}
                for p in vmanager.VerifierManager.get_all(platform=platform)]

    def create(self, name, vtype, platform=None, source=None, version=None,
               system_wide=False, extra_settings=None):
        """Create a verifier.

        :param name: Verifier name
        :param vtype: Verifier plugin name
        :param platform: Verifier plugin platform. Should be specified when
                          there are two verifier plugins with equal names but
                          in different platforms
        :param source: Path or URL to the repo to clone verifier from
        :param version: Branch, tag or commit ID to checkout before
                        verifier installation
        :param system_wide: Whether or not to use the system-wide environment
                            for verifier instead of a virtual environment
        :param extra_settings: Extra installation settings for verifier
        """
        # check that the specified verifier type exists
        vmanager.VerifierManager.get(vtype, platform=platform)

        LOG.info("Creating verifier '%s'." % name)

        try:
            verifier = self._get(name)
        except exceptions.DBRecordNotFound:
            verifier = objects.Verifier.create(
                name=name, source=source, system_wide=system_wide,
                version=version, vtype=vtype, platform=platform,
                extra_settings=extra_settings)
        else:
            raise exceptions.RallyException(
                "Verifier with name '%s' already exists! Please, specify "
                "another name for verifier and try again." % verifier.name)

        properties = {}
        properties["platform"] = platform or verifier.manager.get_platform()

        default_source = verifier.manager._meta_get("default_repo")
        if not source and default_source:
            properties["source"] = default_source

        if properties:
            verifier.update_properties(**properties)

        verifier.update_status(consts.VerifierStatus.INSTALLING)
        try:
            verifier.manager.install()
        except Exception:
            verifier.update_status(consts.VerifierStatus.FAILED)
            raise
        verifier.update_status(consts.VerifierStatus.INSTALLED)

        LOG.info("Verifier %s has been successfully created!" % verifier)

        return verifier.uuid

    def _get(self, verifier_id):
        """Get a verifier.

        :param verifier_id: Verifier name or UUID
        """
        return objects.Verifier.get(verifier_id)

    def get(self, verifier_id):
        return self._get(verifier_id).to_dict()

    def _list(self, status=None):
        """List all verifiers.

        :param status: Status to filter verifiers by
        """
        return objects.Verifier.list(status)

    def list(self, status=None):
        return [item.to_dict() for item in self._list(status)]

    def delete(self, verifier_id, deployment_id=None, force=False):
        """Delete a verifier.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID. If specified,
                              only the deployment-specific data will be deleted
                              for verifier
        :param force: Delete all stored verifier verifications.
                      If deployment_id specified, only verifications of this
                      deployment will be deleted
        """
        verifier = self._get(verifier_id)
        verifications = self.api.verification.list(
            verifier_id=verifier_id,
            deployment_id=deployment_id)
        if verifications:
            d_msg = ((" for deployment '%s'" % deployment_id)
                     if deployment_id else "")
            if force:
                LOG.info("Deleting all verifications created by verifier %s%s."
                         % (verifier, d_msg))
                for verification in verifications:
                    self.api.verification.delete(
                        verification_uuid=verification["uuid"])
            else:
                raise exceptions.RallyException(
                    "Failed to delete verifier {0} because there are stored "
                    "verifier verifications{1}! Please, make sure that they "
                    "are not important to you. Use 'force' flag if you would "
                    "like to delete verifications{1} as well."
                    .format(verifier, d_msg))

        if deployment_id:
            LOG.info("Deleting deployment-specific data for verifier %s."
                     % verifier)
            verifier.set_env(deployment_id)
            verifier.manager.uninstall()
            LOG.info("Deployment-specific data has been successfully deleted!")
        else:
            LOG.info("Deleting verifier %s." % verifier)
            verifier.manager.uninstall(full=True)
            objects.Verifier.delete(verifier_id)
            LOG.info("Verifier has been successfully deleted!")

    def update(self, verifier_id, system_wide=None, version=None,
               update_venv=False):
        """Update a verifier.

        :param verifier_id: Verifier name or UUID
        :param system_wide: Switch to using the system-wide environment
        :param version: Branch, tag or commit ID to checkout
        :param update_venv: Update the virtual environment for verifier
        """
        if system_wide is None and version is None and not update_venv:
            # nothing to update
            raise exceptions.RallyException(
                "At least one of the following parameters should be "
                "specified: 'system_wide', 'version', 'update_venv'.")

        verifier = self._get(verifier_id)
        LOG.info("Updating verifier %s." % verifier)

        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to update verifier %s because verifier is in '%s' "
                "status, but should be in '%s'." % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        system_wide_in_use = (system_wide or
                              (system_wide is None and verifier.system_wide))
        if update_venv and system_wide_in_use:
            raise exceptions.RallyException(
                "It is impossible to update the virtual environment for "
                "verifier %s when it uses the system-wide environment."
                % verifier)

        # store original status to set it again after updating or rollback
        original_status = verifier.status
        verifier.update_status(consts.VerifierStatus.UPDATING)

        properties = {}  # store new verifier properties to update old ones

        sw_is_checked = False

        if version:
            properties["version"] = version

            backup = utils.BackupHelper()
            rollback_msg = ("Failed to update verifier %s. It has been "
                            "rollbacked to the previous state." % verifier)
            backup.add_rollback_action(LOG.info, rollback_msg)
            backup.add_rollback_action(verifier.update_status, original_status)
            with backup(verifier.manager.repo_dir):
                verifier.manager.checkout(version)

            if system_wide_in_use:
                verifier.manager.check_system_wide()
                sw_is_checked = True

        if system_wide is not None:
            if system_wide == verifier.system_wide:
                LOG.info(
                    "Verifier %s is already switched to system_wide=%s. "
                    "Nothing will be changed."
                    % (verifier, verifier.system_wide))
            else:
                properties["system_wide"] = system_wide
                if not system_wide:
                    update_venv = True  # we need to install a virtual env
                else:
                    # NOTE(andreykurilin): should we remove previously created
                    #   virtual environment?!
                    if not sw_is_checked:
                        verifier.manager.check_system_wide()

        if update_venv:
            backup = utils.BackupHelper()
            rollback_msg = ("Failed to update the virtual environment for "
                            "verifier %s. It has been rollbacked to the "
                            "previous state." % verifier)
            backup.add_rollback_action(LOG.info, rollback_msg)
            backup.add_rollback_action(verifier.update_status, original_status)
            with backup(verifier.manager.venv_dir):
                verifier.manager.install_venv()

        properties["status"] = original_status  # change verifier status back
        verifier.update_properties(**properties)

        LOG.info("Verifier %s has been successfully updated!" % verifier)

        return verifier.uuid

    def configure(self, verifier, deployment_id, extra_options=None,
                  reconfigure=False):
        """Configure a verifier.

        :param verifier: Verifier object or (name or UUID)
        :param deployment_id: Deployment name or UUID
        :param extra_options: Extend verifier configuration with extra options
        :param reconfigure: Reconfigure verifier
        """
        if not isinstance(verifier, objects.Verifier):
            verifier = self._get(verifier)
        verifier.set_env(deployment_id)
        LOG.info("Configuring verifier %s for deployment '%s' (UUID=%s)."
                 % (verifier,
                    verifier.deployment["name"],
                    verifier.deployment["uuid"]))

        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to configure verifier %s for deployment '%s' "
                "(UUID=%s) because verifier is in '%s' status, but should be "
                "in '%s'." % (verifier, verifier.deployment["name"],
                              verifier.deployment["uuid"], verifier.status,
                              consts.VerifierStatus.INSTALLED))

        msg = ("Verifier %s has been successfully configured for deployment "
               "'%s' (UUID=%s)!" % (verifier, verifier.deployment["name"],
                                    verifier.deployment["uuid"]))
        vm = verifier.manager
        if vm.is_configured():
            LOG.info("Verifier is already configured!")
            if not reconfigure:
                if not extra_options:
                    return vm.get_configuration()
                else:
                    # Just add extra options to the config file.
                    if logging.is_debug():
                        LOG.debug("Adding the following extra options: %s "
                                  "to verifier configuration." % extra_options)
                    else:
                        LOG.info(
                            "Adding extra options to verifier configuration.")
                    vm.extend_configuration(extra_options)
                    LOG.info(msg)
                    return vm.get_configuration()

            LOG.info("Reconfiguring verifier.")

        raw_config = vm.configure(extra_options=extra_options)

        LOG.info(msg)

        return raw_config

    def override_configuration(self, verifier_id, deployment_id,
                               new_configuration):
        """Override verifier configuration (e.g., rewrite the config file).

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param new_configuration: New configuration for verifier
        """
        verifier = self._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to override verifier configuration for deployment "
                "'%s' (UUID=%s) because verifier %s is in '%s' status, but "
                "should be in '%s'." % (
                    verifier.deployment["name"], verifier.deployment["uuid"],
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        verifier.set_env(deployment_id)
        LOG.info("Overriding configuration of verifier %s for deployment '%s' "
                 "(UUID=%s)."
                 % (verifier,
                    verifier.deployment["name"], verifier.deployment["uuid"]))
        verifier.manager.override_configuration(new_configuration)
        LOG.info("Configuration of verifier %s has been successfully "
                 "overridden for deployment '%s' (UUID=%s)!"
                 % (verifier,
                    verifier.deployment["name"], verifier.deployment["uuid"]))

    def list_tests(self, verifier_id, pattern=""):
        """List all verifier tests.

        :param verifier_id: Verifier name or UUID
        :param pattern: Pattern which will be used for matching
        """
        verifier = self._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to list verifier tests because verifier %s is in '%s' "
                "status, but should be in '%s'." % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        if pattern:
            verifier.manager.validate_args({"pattern": pattern})

        return verifier.manager.list_tests(pattern)

    def add_extension(self, verifier_id, source, version=None,
                      extra_settings=None):
        """Add a verifier extension.

        :param verifier_id: Verifier name or UUID
        :param source: Path or URL to the repo to clone verifier extension from
        :param version: Branch, tag or commit ID to checkout before
                        installation of the verifier extension
        :param extra_settings: Extra installation settings for verifier
                               extension
        """
        verifier = self._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to add verifier extension because verifier %s "
                "is in '%s' status, but should be in '%s'." % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        LOG.info("Adding extension for verifier %s." % verifier)

        # store original status to rollback it after failure
        original_status = verifier.status
        verifier.update_status(consts.VerifierStatus.EXTENDING)
        try:
            verifier.manager.install_extension(source, version=version,
                                               extra_settings=extra_settings)
        finally:
            verifier.update_status(original_status)

        LOG.info("Extension for verifier %s has been successfully added!"
                 % verifier)

    def list_extensions(self, verifier_id):
        """List all verifier extensions.

        :param verifier_id: Verifier name or UUID
        """
        verifier = self._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to list verifier extensions because verifier %s "
                "is in '%s' status, but should be in '%s.'" % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        return verifier.manager.list_extensions()

    def delete_extension(self, verifier_id, name):
        """Delete a verifier extension.

        :param verifier_id: Verifier name or UUID
        :param name: Verifier extension name
        """
        verifier = self._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to delete verifier extension because verifier %s "
                "is in '%s' status, but should be in '%s'." % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        LOG.info("Deleting extension for verifier %s." % verifier)
        verifier.manager.uninstall_extension(name)
        LOG.info("Extension for verifier %s has been successfully deleted!"
                 % verifier)


class _Verification(APIGroup):

    def start(self, verifier_id, deployment_id, tags=None, **run_args):
        """Start a verification.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param tags: List of tags to assign them to verification
        :param run_args: Dictionary with run arguments for verification
        """
        # TODO(ylobankov): Add an ability to skip tests by specifying only test
        #                  names (without test IDs). Also, it would be nice to
        #                  skip the whole test suites. For example, all tests
        #                  in the class or module.

        deployment = objects.Deployment.get(deployment_id)

        if deployment["status"] != consts.DeployStatus.DEPLOY_FINISHED:
            raise exceptions.DeploymentNotFinishedStatus(
                name=deployment["name"],
                uuid=deployment["uuid"],
                status=deployment["status"])

        verifier = self.api.verifier._get(verifier_id)
        if verifier.status != consts.VerifierStatus.INSTALLED:
            raise exceptions.RallyException(
                "Failed to start verification because verifier %s is in '%s' "
                "status, but should be in '%s'." % (
                    verifier, verifier.status, consts.VerifierStatus.INSTALLED)
            )

        verifier.set_env(deployment_id)
        if not verifier.manager.is_configured():
            self.api.verifier.configure(verifier=verifier,
                                        deployment_id=deployment_id)

        # TODO(andreykurilin): save validation results to db
        verifier.manager.validate(run_args)

        verification = objects.Verification.create(
            verifier_id=verifier_id, deployment_id=deployment_id, tags=tags,
            run_args=run_args)
        LOG.info("Starting verification (UUID=%s) for deployment '%s' "
                 "(UUID=%s) by verifier %s."
                 % (verification.uuid,
                    verifier.deployment["name"],
                    verifier.deployment["uuid"],
                    verifier))
        verification.update_status(consts.VerificationStatus.RUNNING)

        context = {"config": verifier.manager._meta_get("context"),
                   "run_args": run_args,
                   "verification": verification,
                   "verifier": verifier}
        try:
            with vcontext.ContextManager(context):
                results = verifier.manager.run(context)
        except Exception as e:
            verification.set_error(e)
            raise

        # TODO(ylobankov): Check that verification exists in the database
        #                  because users may delete verification before tests
        #                  finish.
        verification.finish(results.totals, results.tests)

        LOG.info("Verification (UUID=%s) has been successfully finished for "
                 "deployment '%s' (UUID=%s)!"
                 % (verification.uuid,
                    verifier.deployment["name"], verifier.deployment["uuid"]))

        return {"verification": verification.to_dict(),
                "totals": results.totals,
                "tests": results.tests}

    def rerun(self, verification_uuid, deployment_id=None, failed=False,
              tags=None, concurrency=0):
        """Rerun tests from a verification.

        :param verification_uuid: Verification UUID
        :param deployment_id: Deployment name or UUID
        :param failed: Rerun only failed tests
        :param tags: List of tags to assign them to verification
        :param concurrency: The number of processes to use to run verifier
            tests
        """
        # TODO(ylobankov): Improve this method in the future: put some
        #                  information about re-run in run_args.
        run_args = {}
        if concurrency:
            run_args["concurrency"] = concurrency

        verification = self._get(verification_uuid)
        tests = verification.tests

        if failed:
            tests = [t for t, r in tests.items() if r["status"] == "fail"]
            if not tests:
                raise exceptions.RallyException(
                    "There are no failed tests from verification (UUID=%s)."
                    % verification_uuid)
        else:
            tests = tests.keys()

        deployment = (deployment_id if deployment_id
                      else verification.deployment_uuid)
        deployment = self.api.deployment.get(deployment=deployment)
        LOG.info("Re-running %stests from verification (UUID=%s) for "
                 "deployment '%s' (UUID=%s)."
                 % ("failed " if failed else "",
                    verification.uuid,
                    deployment["name"], deployment["uuid"]))
        return self.start(verifier_id=verification.verifier_uuid,
                          deployment_id=deployment["uuid"],
                          load_list=tests, tags=tags, **run_args)

    def _get(self, verification_uuid):
        """Get a verification.

        :param verification_uuid: Verification UUID
        """
        return objects.Verification.get(verification_uuid)

    def get(self, verification_uuid):
        return self._get(verification_uuid).to_dict()

    def list(self, verifier_id=None, deployment_id=None,
             tags=None, status=None):
        """List all verifications.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param tags: Tags to filter verifications by
        :param status: Status to filter verifications by
        """
        return [item.to_dict() for item in objects.Verification.list(
            verifier_id, deployment_id=deployment_id,
            tags=tags, status=status)]

    def delete(self, verification_uuid):
        """Delete a verification.

        :param verification_uuid: Verification UUID
        """
        verification = self._get(verification_uuid)
        LOG.info("Deleting verification (UUID=%s)." % verification.uuid)
        verification.delete()
        LOG.info("Verification has been successfully deleted!")

    def report(self, uuids, output_type, output_dest=None):
        """Generate a report for a verification or a few verifications.

        :param uuids: List of verifications UUIDs
        :param output_type: Plugin name of verification reporter
        :param output_dest: Destination for verification report
        """
        verifications = [self._get(uuid) for uuid in uuids]

        reporter_cls = vreporter.VerificationReporter.get(output_type)
        reporter_cls.validate(output_dest)

        LOG.info("Building '%s' report for the following verification(s): '%s'"
                 % (output_type, "', '".join(uuids)))
        result = vreporter.VerificationReporter.make(reporter_cls,
                                                     verifications,
                                                     output_dest)
        LOG.info("The report has been successfully built.")
        return result

    def import_results(self, verifier_id, deployment_id, data, **run_args):
        """Import results of a test run into Rally database.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param data: Results data of a test run to import
        :param run_args: Dictionary with run arguments
        """
        # TODO(aplanas): Create an external deployment if this is missing, as
        # required in the blueprint [1].
        # [1] https://blueprints.launchpad.net/rally/+spec/verification-import

        verifier = self.api.verifier._get(verifier_id)
        verifier.set_env(deployment_id)
        LOG.info("Importing test results into a new verification for "
                 "deployment '%s' (UUID=%s), using verifier %s."
                 % (verifier.deployment["name"],
                    verifier.deployment["uuid"],
                    verifier))

        verifier.manager.validate_args(run_args)

        verification = objects.Verification.create(verifier_id,
                                                   deployment_id=deployment_id,
                                                   run_args=run_args)
        verification.update_status(consts.VerificationStatus.RUNNING)

        try:
            results = verifier.manager.parse_results(data)
        except Exception as e:
            verification.set_failed(e)
            raise
        verification.finish(results.totals, results.tests)

        LOG.info("Test results have been successfully imported.")

        return {"verification": verification.to_dict(),
                "totals": results.totals,
                "tests": results.tests}


class API(object):

    CONFIG_SEARCH_PATHS = [sys.prefix + "/etc/rally", "~/.rally", "/etc/rally"]
    CONFIG_FILE_NAME = "rally.conf"

    def __init__(self, config_file=None, config_args=None,
                 plugin_paths=None, skip_db_check=False):
        """Initialize Rally API instance

        :param config_file: Path to rally configuration file. If None, default
                            path will be selected
        :type config_file: str
        :param config_args: Arguments for initialization current configuration
        :type config_args: list
        :param plugin_paths: Additional custom plugin locations
        :type plugin_paths: list
        :param skip_db_check: Allows to skip db revision check
        :type skip_db_check: bool
        """

        try:
            config_files = ([config_file] if config_file else
                            self._default_config_file())
            CONF(config_args or [],
                 project="rally",
                 version=rally_version.version_string(),
                 default_config_files=config_files)
            CONF.set_default("use_stderr", True)

            logging.setup("rally")
            if not CONF.get("log_config_append"):
                # The below two lines are to disable noise from request module.
                # The standard way should be we make such lots of settings on
                # the root rally. However current oslo codes doesn't support
                # such interface. So I choose to use a 'hacking' way to avoid
                # INFO logs from request module where user didn't give specific
                # log configuration. And we could remove this hacking after
                # oslo.log has such interface.
                LOG.debug(
                    "INFO logs from urllib3 and requests module are hide.")
                requests_log = logging.getLogger("requests").logger
                requests_log.setLevel(logging.WARNING)
                urllib3_log = logging.getLogger("urllib3").logger
                urllib3_log.setLevel(logging.WARNING)

                LOG.debug("urllib3 insecure warnings are hidden.")
                for warning in ("InsecurePlatformWarning",
                                "SNIMissingWarning",
                                "InsecureRequestWarning"):
                    warning_cls = getattr(urllib3.exceptions, warning, None)
                    if warning_cls is not None:
                        urllib3.disable_warnings(warning_cls)

            # NOTE(wtakase): This is for suppressing boto error logging.
            LOG.debug("ERROR log from boto module is hide.")
            boto_log = logging.getLogger("boto").logger
            boto_log.setLevel(logging.CRITICAL)

            # Set alembic log level to ERROR
            alembic_log = logging.getLogger("alembic").logger
            alembic_log.setLevel(logging.ERROR)

        except cfg.ConfigFilesNotFoundError as e:
            cfg_files = e.config_files
            raise exceptions.RallyException(
                "Failed to read configuration file(s): %s" % cfg_files)

        # Check that db is upgraded to the latest revision
        if not skip_db_check:
            self.check_db_revision()

        # Load plugins
        plugin_paths = plugin_paths or []
        if "plugin_paths" in CONF:
            plugin_paths.extend(CONF.get("plugin_paths") or [])
        for path in plugin_paths:
            discover.load_plugins(path)

        # NOTE(andreykurilin): There is no reason to auto-discover API's. We
        # have only 4 classes, so let's do it in good old way - hardcode them:)
        self._deployment = _Deployment(self)
        self._task = _Task(self)
        self._verifier = _Verifier(self)
        self._verification = _Verification(self)

    def _default_config_file(self):
        for path in self.CONFIG_SEARCH_PATHS:
            abspath = os.path.abspath(os.path.expanduser(path))
            fpath = os.path.join(abspath, self.CONFIG_FILE_NAME)
            if os.path.isfile(fpath):
                return [fpath]

    def check_db_revision(self):
        rev = rally_version.database_revision()

        # Check that db exists
        if rev["revision"] is None:
            raise exceptions.RallyException(
                "Database is missing. Create database by command "
                "`rally db create'")

        # Check that db is updated
        if rev["revision"] != rev["current_head"]:
            raise exceptions.RallyException((
                "Database seems to be outdated. Run upgrade from "
                "revision %(revision)s to %(current_head)s by command "
                "`rally db upgrade'") % rev)

    def _request(self, path, method, **kwargs):
        headers = {
            "RALLY-CLIENT-VERSION": rally_version.version_string(),
            "RALLY-API": "1.0"
        }
        response = requests.request(method, path,
                                    json=kwargs, headers=headers)
        if response.status_code != 200:
            raise exceptions.find_exception(response)

        return response.json(
            object_pairs_hook=collections.OrderedDict)["result"]

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

    @property
    def version(self):
        return 1
