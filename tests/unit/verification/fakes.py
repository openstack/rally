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


def get_fake_test_case():
    return {
        "total": {
            "failures": 1,
            "tests": 2,
            "expected_failures": 0,
            "time": 1.412},
        "test_cases": {
            "fake.failed.TestCase.with_StringException[gate,negative]": {
                "name":
                    "fake.failed.TestCase.with_StringException[gate,negative]",
                "traceback": ("_StringException: Empty attachments:\nOops..."
                              "There was supposed to be fake traceback, but it"
                              " is not.\n"),
                "time": 0.706,
                "status": "fail"},
            "fake.successful.TestCase.fake_test[gate,negative]": {
                "name": "fake.successful.TestCase.fake_test[gate,negative]",
                "time": 0.706,
                "status": "success"
            }
        }
    }
