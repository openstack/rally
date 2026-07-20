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

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = """
module: synchronize
short_description: Lint-only stub for Zuul's synchronize action plugin
description: Lint-only stub. See the module source for details.
options:
  src:
    description: Stub option.
    type: str
  dest:
    description: Stub option.
    type: str
  mode:
    description: Stub option.
    type: str
  copy_links:
    description: Stub option.
    type: bool
  verify_host:
    description: Stub option.
    type: bool
  rsync_opts:
    description: Stub option.
    type: list
    elements: str
author:
  - rally (@xrally)
"""


def main():
    AnsibleModule(
        argument_spec=dict(
            src=dict(type="str"),
            dest=dict(type="str"),
            mode=dict(type="str"),
            copy_links=dict(type="bool"),
            verify_host=dict(type="bool"),
            rsync_opts=dict(type="list", elements="str"),
        ),
        supports_check_mode=True,
    ).exit_json(changed=False)


if __name__ == "__main__":
    main()
