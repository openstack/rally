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

from rally import exceptions

PATH_GLOBALS = "~/.rally/globals"
ENV_ENV = "RALLY_ENV"
ENV_DEPLOYMENT = "RALLY_DEPLOYMENT"
ENV_TASK = "RALLY_TASK"
ENV_VERIFIER = "RALLY_VERIFIER"
ENV_VERIFICATION = "RALLY_VERIFICATION"
ENVVARS = [ENV_ENV, ENV_DEPLOYMENT, ENV_TASK, ENV_VERIFIER, ENV_VERIFICATION]

MSG_MISSING_ARG = "Missing argument: --%(arg_name)s"


def _read_env_file(path, except_env=None):
    """Read the environment variable file.

    :param path: the path of the file
    :param except_env: the environment variable to avoid in the output

    :returns: the content of the original file except the line starting with
    the except_env parameter
    """
    output = []
    if os.path.exists(path):
        with open(path, "r") as env_file:
            content = env_file.readlines()
            for line in content:
                if except_env is None or not line.startswith("%s=" %
                                                             except_env):
                    output.append(line)
    return output


def _load_env_file(path):
    """Load the environment variable file into os.environ.

    :param path: the path of the file
    """
    if os.path.exists(path):
        content = _read_env_file(path)
        for line in content:
            (key, sep, value) = line.partition("=")
            os.environ[key] = value.rstrip()


def _rewrite_env_file(path, initial_content):
    """Rewrite the environment variable file.

    :param path: the path of the file
    :param initial_content: the original content of the file
    """
    with open(path, "w+") as env_file:
        for line in initial_content:
            env_file.write(line)


def _update_env_file(path, env_key, env_value):
    """Update the environment variable file.

    :param path: the path of the file
    :param env_key: the key to update
    :param env_value: the value of the property to update
    """
    output = _read_env_file(path, env_key)
    output.append("%s=%s" % (env_key, env_value))
    _rewrite_env_file(path, output)


def update_globals_file(key, value):
    """Update the globals variables file.

    :param key: the key to update
    :param value: the value to update
    """
    dir = os.path.expanduser("~/.rally/")
    if not os.path.exists(dir):
        os.makedirs(dir)
    expanded_path = os.path.join(dir, "globals")
    _update_env_file(expanded_path, key, "%s\n" % value)


def clear_global(global_key):
    path = os.path.expanduser(PATH_GLOBALS)
    if os.path.exists(path):
        _update_env_file(path, global_key, "\n")
    if global_key in os.environ:
        os.environ.pop(global_key)


def clear_env():
    for envvar in ENVVARS:
        clear_global(envvar)


def get_global(global_key, do_raise=False):
    if global_key not in os.environ:
        _load_env_file(os.path.expanduser(PATH_GLOBALS))
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


def with_default_env():
    # NOTE(boris-42): This allows smooth transition from deployment to env
    #                 set ENV_ENV from ENV_DEPLOYMENT if ENV is not presented
    #                 This should be removed with rally env command
    if not get_global(ENV_ENV):
        deployment = get_global(ENV_DEPLOYMENT)
        if deployment:
            os.environ[ENV_ENV] = deployment

    return default_from_global(
        "env", ENV_ENV, "env",
        message="There is no default env. To set it use command:\n"
                "\trally env use <env_uuid>|<env_name>\n"
                "or pass uuid or name to your command using --%(arg_name)s")


def with_default_deployment(cli_arg_name="uuid"):
    # NOTE(boris-42): This allows smooth transition from deployment to env
    #                 set ENV_ENV from ENV_DEPLOYMENT and use ENV_ENV
    #                 This should be removed with rally env command
    if not get_global(ENV_ENV):
        deployment = get_global(ENV_DEPLOYMENT)
        if deployment:
            os.environ[ENV_ENV] = deployment

    return default_from_global(
        "deployment", ENV_ENV, cli_arg_name,
        message="There is no default deployment.\n"
                "\tPlease use command:\n"
                "\trally deployment use <deployment_uuid>|<deployment_name>\n"
                "or pass uuid of deployment to the --%(arg_name)s "
                "argument of this command")


def with_default_verifier_id(cli_arg_name="id"):
    return default_from_global("verifier_id", ENV_VERIFIER, cli_arg_name)


with_default_task_id = default_from_global("task_id", ENV_TASK, "uuid")
with_default_verification_uuid = default_from_global("verification_uuid",
                                                     ENV_VERIFICATION, "uuid")
