# Copyright 2014: Mirantis Inc.
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


class ValidationResult(object):

    def __init__(self, is_valid=True, msg=None):
        self.is_valid = is_valid
        self.msg = msg


def add_validator(validator):
    def wrapper(func):
        if not getattr(func, 'validators', None):
            func.validators = []
        func.validators.append(validator)
        return func
    return wrapper
