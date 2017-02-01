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

.. _howto-add-new-reporting-mechanism:

=================================
HowTo add new reporting mechanism
=================================

Reporting mechanism for verifications is pluggable. Custom plugins can be used
for custom output formats or for exporting results to external systems.

We hardly recommend to read :ref:`plugins` page to understand how do Rally
Plugins work.

.. contents::
  :depth: 2
  :local:

Spec
----

All reporters should inherit
``rally.verification.reporter.VerificationReporter`` and implement all
abstract methods. Here you can find its interface:

    .. autoclass:: rally.verification.reporter.VerificationReporter
       :members:

Example of custom JSON Reporter
-------------------------------

Basically, you need to implement only two methods "validate" and "generate".

Method "validate" should check that destination of the report is right.
Method "generate" should build a report or export results somewhere; actually,
it is up to you what it should do but return format is strict, see
`Spec <#spec>`_ section for what it can return.

.. code-block:: python

    import json

    from rally.verification import reporter


    @reporter.configure("summary-in-json")
    class SummaryInJsonReporter(reporter.VerificationReporter):
        """Store summary of verification(s) in JSON format"""

        # ISO 8601
        TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

        @classmethod
        def validate(cls, output_destination):
            # we do not have any restrictions for destination, so nothing to
            # check
            pass

        def generate(self):
            report = {}

            for v in self.verifications:
                report[v.uuid] = {
                    "started_at": v.created_at.strftime(self.TIME_FORMAT),
                    "finished_at": v.updated_at.strftime(self.TIME_FORMAT),
                    "status": v.status,
                    "run_args": v.run_args,
                    "tests_count": v.tests_count,
                    "tests_duration": v.tests_duration,
                    "skipped": v.skipped,
                    "success": v.success,
                    "expected_failures": v.expected_failures,
                    "unexpected_success": v.unexpected_success,
                    "failures": v.failures,
                    # v.tests includes all information about launched tests,
                    # but for simplification of this fake reporters, let's
                    # save just names
                    "launched_tests": [test["name"]
                                       for test in v.tests.values()]
                }

            raw_report = json.dumps(report, indent=4)

            if self.output_destination:
                # In case of output_destination existence report will be saved
                # to hard drive and there is nothing to print to stdout, so
                # "print" key is not used
                return {"files": {self.output_destination: raw_report},
                        "open": self.output_destination}
            else:
                # it is something that will be print at CLI layer.
                return {"print": raw_report}

