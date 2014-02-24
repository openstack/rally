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
import decorator
import os

from rally import exceptions
from rally import fileutils


def _default_deployment_id():
    try:
        deploy_id = os.environ['RALLY_DEPLOYMENT']
    except KeyError:
        fileutils.load_env_file(os.path.expanduser('~/.rally/globals'))
        try:
            deploy_id = os.environ['RALLY_DEPLOYMENT']
        except KeyError:
            raise exceptions.InvalidArgumentsException(
                "deploy-id argument is missing")
    return deploy_id


@decorator.decorator
def deploy_id_default(f, *args, **kwargs):
    deploy_id_arg_index = f.func_code.co_varnames.index("deploy_id")
    args = list(args)
    if args[deploy_id_arg_index] is None:
        args[deploy_id_arg_index] = _default_deployment_id()
    return f(*args, **kwargs)
