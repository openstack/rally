..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _howto-add-support-for-new-tool:

==============================
HowTo add support for new tool
==============================

First of all, you should start from the reading of :ref:`plugins` page.
After you learned basic things about Rally plugin mechanism, let's move to
Verifier interface itself.

.. contents::
  :depth: 2
  :local:

Spec
----

All verifiers plugins should inherit
``rally.verification.manager.VerifierManager`` and implement all abstract
methods. Here you can find its interface:

    .. autoclass:: rally.verification.manager.VerifierManager
       :members:
       :exclude-members: base_ref, check_system_wide, checkout, install_venv,
         parse_results, validate


Example of Fake Verifier Manager
--------------------------------

FakeTool is a tool which doesn't require configuration and installation.

  .. code-block:: python

       import random
       import re

       from rally.verification import manager


       # Verification component expects that method "run" of verifier returns
       # object. Class Result is a simple wrapper for two expected properties.
       class Result(object):
           def __init__(self, totals, tests):
               self.totals = totals
               self.tests = tests


       @manager.configure("fake-tool", default_repo="https://example.com")
       class FakeTool(manager.VerifierManager):
           """Fake Tool \o/"""

           TESTS = ["fake_tool.tests.bar.FatalityTestCase.test_one",
                    "fake_tool.tests.bar.FatalityTestCase.test_two",
                    "fake_tool.tests.bar.FatalityTestCase.test_three",
                    "fake_tool.tests.bar.FatalityTestCase.test_four",
                    "fake_tool.tests.foo.MegaTestCase.test_one",
                    "fake_tool.tests.foo.MegaTestCase.test_two",
                    "fake_tool.tests.foo.MegaTestCase.test_three",
                    "fake_tool.tests.foo.MegaTestCase.test_four"]

           # This fake verifier doesn't launch anything, just returns random
           #  results, so let's override parent methods to avoid redundant
           #  clonning repo, checking packages and so on.

           def install(self):
               pass

           def uninstall(self, full=False):
               pass

           # Each tool, which supports configuration, has the own mechanism
           # for that task. Writing unified method is impossible. That is why
           # `VerificationManager` implements the case when the tool doesn't
           # need (doesn't support) configuration at all. Such behaviour is
           # ideal for FakeTool, since we do not need to change anything :)

           # Let's implement method `run` to return random data.
           def run(self, context):
               totals = {"tests_count": len(self.TESTS),
                         "tests_duration": 0,
                         "failures": 0,
                         "skipped": 0,
                         "success": 0,
                         "unexpected_success": 0,
                         "expected_failures": 0}
               tests = {}
               for name in self.TESTS:
                   duration = random.randint(0, 10000)/100.
                   totals["tests_duration"] += duration
                   test = {"name": name,
                           "status": random.choice(["success", "fail"]),
                           "duration": "%s" % duration}
                   if test["status"] == "fail":
                       test["traceback"] = "Ooooppps"
                       totals["failures"] += 1
                   else:
                       totals["success"] += 1
                   tests[name] = test
               return Result(totals, tests=tests)

           def list_tests(self, pattern=""):
               return [name for name in self.TESTS if re.match(pattern, name)]
