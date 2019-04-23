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

from rally.env import platform


@platform.configure(name="good", platform="fake")
class GoodPlatform(platform.Platform):

    CONFIG_SCHEMA = {}

    def create(self):
        return {}, {}

    def destroy(self):
        pass

    def cleanup(self, task_uuid=None):
        return {
            "message": "Coming soon!",
            "discovered": 0,
            "deleted": 0,
            "failed": 0,
            "resources": {},
            "errors": []
        }

    def check_health(self):
        return {"available": True}

    def info(self):
        return {"info": {"a": 1}}

    @classmethod
    def create_spec_from_sys_environ(cls, sys_environ):

        spec = {
            "auth_url": sys_environ.get("OS_AUTH_URL"),
            "username": sys_environ.get("OS_USERNAME"),
            "password": sys_environ.get("OS_PASSWORD")
        }
        return {"spec": spec, "available": True, "message": "Available"}
