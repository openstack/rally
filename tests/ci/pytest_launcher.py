#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import os
import subprocess
import sys


PYTEST_REPORT = os.environ.get("PYTEST_REPORT",
                               ".test_results/pytest_results.html")
TESTR_REPORT = "testr_results.html"
PYTEST_ARGUMENTS = ("py.test"  # base command
                    " --html=%(html_report)s"  # html report
                    " --durations=10"  # get a list of the slowest 10 tests
                    " -n auto"  # launch tests in parallel
                    " --timeout=%(timeout)s"  # timeout for individual test
                    " %(path)s"
                    )


def error(msg):
    print(msg)
    exit(1)


def main(args):
    parser = argparse.ArgumentParser(args[0])
    parser.add_argument("discovery_path", metavar="<path>", type=str,
                        help="Path to location of all tests.")
    parser.add_argument("--posargs", metavar="<str>", type=str, default="",
                        help="TOX posargs. Currently supported only string to "
                             "partial test or tests group to launch.")
    parser.add_argument("--timeout", metavar="<seconds>", type=int, default=60,
                        help="Timeout for individual test execution. "
                             "Defaults to 60")
    args = parser.parse_args(args[1:])

    # We allow only one parameter - path to partial test or tests group
    path = args.posargs
    if len(path.split(" ")) > 1:
        error("Wrong value of posargs. It should include only path to single "
              "test or tests group to launch.")
    # NOTE(andreykurilin): Previously, next format was supported:
    #   tests.unit.test_osclients.SomeTestCase.some_method
    # It is more simple and pythonic than native pytest-way:
    #   tests/unit/test_osclients.py::SomeTestCase::some_method
    # Let's return this support
    if path:
        if "/" not in path:
            path = path.split(".")
            module = ""
            for i in range(0, len(path)):
                part = os.path.join(module, path[i])
                if os.path.exists(part):
                    module = part
                    continue
                if os.path.exists("%s.py" % part):
                    if i != (len(path) - 1):
                        module = "%s.py::%s" % (part, "::".join(path[i + 1:]))
                    else:
                        module = "%s.py" % part
                    break

                error("Non-existing path to single test or tests group to "
                      "launch. %s %s" % (module, part))
            path = module

        path = os.path.abspath(os.path.expanduser(path))
        if not path.startswith(os.path.abspath(args.discovery_path)):
            # Prevent to launch functional tests from unit tests launcher.
            error("Wrong path to single test or tests group to launch. It "
                  "should be in %s." % args.discovery_path)
    else:
        path = args.discovery_path

    print("Test(s) to launch (pytest format): %s" % path)

    # NOTE(andreykurilin): we cannot publish pytest reports at gates, but we
    #   can mask them as testr reports. It looks like a dirty hack and I
    #   prefer to avoid it, but I see no other solutions at this point.

    # apply dirty hack only in gates.
    if os.environ.get("ZUUL_PROJECT"):
        pytest_report = TESTR_REPORT
    else:
        pytest_report = PYTEST_REPORT

    args = PYTEST_ARGUMENTS % {"html_report": pytest_report,
                               "path": path,
                               "timeout": args.timeout}
    try:
        subprocess.check_call(args.split(" "),
                              stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        # NOTE(andreykurilin): it is ok, since tests can fail.
        exit_code = 1
    else:
        exit_code = 0

    if os.path.exists(pytest_report) and os.environ.get("ZUUL_PROJECT"):
        subprocess.check_call(["gzip", "-9", "-f", pytest_report],
                              stderr=subprocess.STDOUT)

    if exit_code == 1:
        error("")

if __name__ == "__main__":
    sys.exit(main(sys.argv))
