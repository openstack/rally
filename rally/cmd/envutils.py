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


def get_global(global_key, do_raise=False):
    if global_key not in os.environ:
        fileutils.load_env_file(os.path.expanduser('~/.rally/globals'))
    value = os.environ.get(global_key)
    if not value and do_raise:
        raise exceptions.InvalidArgumentsException('%s env is missing'
                                                   % global_key)
    return value


def default_from_global(arg_name, env_name):
    def default_from_global(f, *args, **kwargs):
        id_arg_index = f.func_code.co_varnames.index(arg_name)
        args = list(args)
        if args[id_arg_index] is None:
            args[id_arg_index] = get_global(env_name, do_raise=True)
        return f(*args, **kwargs)
    return decorator.decorator(default_from_global)


with_default_deploy_id = default_from_global('deploy_id', 'RALLY_DEPLOYMENT')
with_default_task_id = default_from_global('task_id', 'RALLY_TASK')
