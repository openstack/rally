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

import os

import decorator
from oslo_utils import strutils

from rally.common import fileutils
from rally.common.i18n import _
from rally import exceptions

ENV_DEPLOYMENT = "RALLY_DEPLOYMENT"
ENV_TASK = "RALLY_TASK"
ENV_VERIFICATION = "RALLY_VERIFICATION"
ENVVARS = [ENV_DEPLOYMENT, ENV_TASK, ENV_VERIFICATION]

MSG_MISSING_ARG = _("Missing argument: --%(arg_name)s")


def clear_global(global_key):
    path = os.path.expanduser("~/.rally/globals")
    if os.path.exists(path):
        fileutils.update_env_file(path, global_key, "\n")
    if global_key in os.environ:
        os.environ.pop(global_key)


def clear_env():
    for envvar in ENVVARS:
        clear_global(envvar)


def get_global(global_key, do_raise=False):
    if global_key not in os.environ:
        fileutils.load_env_file(os.path.expanduser("~/.rally/globals"))
    value = os.environ.get(global_key)
    if not value and do_raise:
        raise exceptions.InvalidArgumentsException("%s env is missing"
                                                   % global_key)
    return value


def default_from_global(arg_name, env_name,
                        cli_arg_name,
                        message=MSG_MISSING_ARG):
    def default_from_global(f, *args, **kwargs):
        id_arg_index = f.__code__.co_varnames.index(arg_name)
        args = list(args)
        if args[id_arg_index] is None:
            args[id_arg_index] = get_global(env_name)
            if not args[id_arg_index]:
                print(message % {"arg_name": cli_arg_name})
                return(1)
        return f(*args, **kwargs)
    return decorator.decorator(default_from_global)


def with_default_deployment(cli_arg_name="uuid"):
    return default_from_global("deployment", ENV_DEPLOYMENT, cli_arg_name,
                               message=_("There is no default deployment.\n"
                                         "\tPlease use command:\n"
                                         "\trally deployment use "
                                         "<deployment_uuid>|<deployment_name>"
                                         "\nor pass uuid of deployment to "
                                         "the --%(arg_name)s argument of "
                                         "this command"))

with_default_task_id = default_from_global("task_id", ENV_TASK, "uuid")
with_default_verification_id = default_from_global(
    "verification", ENV_VERIFICATION, "uuid")


def get_creds_from_env_vars():
    required_env_vars = ["OS_AUTH_URL", "OS_USERNAME", "OS_PASSWORD"]
    missing_env_vars = [v for v in required_env_vars if v not in os.environ]
    if missing_env_vars:
        msg = ("The following environment variables are "
               "required but not set: %s" % " ".join(missing_env_vars))
        raise exceptions.ValidationError(message=msg)

    creds = {
        "auth_url": os.environ["OS_AUTH_URL"],
        "admin": {
            "username": os.environ["OS_USERNAME"],
            "password": os.environ["OS_PASSWORD"],
            "tenant_name": get_project_name_from_env()
        },
        "endpoint_type": get_endpoint_type_from_env(),
        "endpoint": os.environ.get("OS_ENDPOINT"),
        "region_name": os.environ.get("OS_REGION_NAME", ""),
        "https_cacert": os.environ.get("OS_CACERT", ""),
        "https_insecure": strutils.bool_from_string(
            os.environ.get("OS_INSECURE"))
    }

    user_domain_name = os.environ.get("OS_USER_DOMAIN_NAME")
    project_domain_name = os.environ.get("OS_PROJECT_DOMAIN_NAME")
    if user_domain_name or project_domain_name:
        # it is Keystone v3 and it has another config schem
        creds["admin"]["project_name"] = creds["admin"].pop("tenant_name")
        creds["admin"]["user_domain_name"] = user_domain_name or ""
        creds["admin"]["project_domain_name"] = project_domain_name or ""

    return creds


def get_project_name_from_env():
    tenant_name = os.environ.get("OS_PROJECT_NAME",
                                 os.environ.get("OS_TENANT_NAME"))
    if tenant_name is None:
        raise exceptions.ValidationError("Either the OS_PROJECT_NAME or "
                                         "OS_TENANT_NAME environment variable "
                                         "is required, but neither is set.")

    return tenant_name


def get_endpoint_type_from_env():
    endpoint_type = os.environ.get("OS_ENDPOINT_TYPE",
                                   os.environ.get("OS_INTERFACE"))
    if endpoint_type and "URL" in endpoint_type:
        endpoint_type = endpoint_type.replace("URL", "")

    return endpoint_type
