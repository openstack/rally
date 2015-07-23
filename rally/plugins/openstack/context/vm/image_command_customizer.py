# Copyright 2015: Mirantis Inc.
# All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import copy

from rally import exceptions
from rally.plugins.openstack.context.vm import custom_image
from rally.plugins.openstack.scenarios.vm import utils as vm_utils
import rally.task.context as context


@context.configure(name="image_command_customizer", order=501)
class ImageCommandCustomizerContext(custom_image.BaseCustomImageGenerator):
    """Context class for generating image customized by a command execution.

    Run a command specified by configuration to prepare image.

    Use this script e.g. to download and install something.
    """

    CONFIG_SCHEMA = copy.deepcopy(
        custom_image.BaseCustomImageGenerator.CONFIG_SCHEMA)
    CONFIG_SCHEMA["definitions"] = {
        "stringOrStringList": {
            "anyOf": [
                {"type": "string"},
                {
                    "type": "array",
                    "items": {"type": "string"}
                }
            ]
        },
        "scriptFile": {
            "properties": {
                "script_file": {"$ref": "#/definitions/stringOrStringList"},
                "interpreter": {"$ref": "#/definitions/stringOrStringList"},
                "command_args": {"$ref": "#/definitions/stringOrStringList"}
            },
            "required": ["script_file", "interpreter"],
            "additionalProperties": False,
        },
        "scriptInline": {
            "properties": {
                "script_inline": {"type": "string"},
                "interpreter": {"$ref": "#/definitions/stringOrStringList"},
                "command_args": {"$ref": "#/definitions/stringOrStringList"}
            },
            "required": ["script_inline", "interpreter"],
            "additionalProperties": False,
        },
        "commandPath": {
            "properties": {
                "remote_path": {"$ref": "#/definitions/stringOrStringList"},
                "local_path": {"type": "string"},
                "command_args": {"$ref": "#/definitions/stringOrStringList"}
            },
            "required": ["remote_path"],
            "additionalProperties": False,
        },
        "commandDict": {
            "type": "object",
            "oneOf": [
                {"$ref": "#/definitions/scriptFile"},
                {"$ref": "#/definitions/scriptInline"},
                {"$ref": "#/definitions/commandPath"},
            ],
        }
    }
    CONFIG_SCHEMA["properties"]["command"] = {
        "$ref": "#/definitions/commandDict"
    }

    def _customize_image(self, server, fip, user):
        code, out, err = vm_utils.VMScenario(self.context)._run_command(
            fip["ip"], self.config["port"],
            self.config["username"], self.config.get("password"),
            command=self.config["command"],
            pkey=user["keypair"]["private"])

        if code:
            raise exceptions.ScriptError(
                message="Command `%(command)s' execution failed,"
                " code %(code)d:\n"
                "STDOUT:\n============================\n"
                "%(out)s\n"
                "STDERR:\n============================\n"
                "%(err)s\n"
                "============================\n"
                % {"command": self.config["command"], "code": code,
                   "out": out, "err": err})

        return code, out, err
