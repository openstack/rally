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

import functools
import os
import subprocess
import tempfile

import six

from rally.common.i18n import _
from rally import exceptions


class TempestBenchmarkFailure(exceptions.RallyException):
    msg_fmt = _("Failed tempest test(s): '%(message)s'")


def tempest_log_wrapper(func):
    @functools.wraps(func)
    def inner_func(scenario_obj, *args, **kwargs):
        if "log_file" not in kwargs:
            # set temporary log file
            kwargs["log_file"] = os.path.join(
                scenario_obj.context["tmp_results_dir"],
                os.path.basename(tempfile.NamedTemporaryFile().name))

        # run target scenario
        try:
            func(scenario_obj, *args, **kwargs)
        except subprocess.CalledProcessError:
            pass

        # parse and save results
        results = scenario_obj.context["verifier"].parse_results(
            kwargs["log_file"])
        if results:
            total = results.total
            test_execution = float(total["time"])
            scenario_obj._atomic_actions["test_execution"] = test_execution
            if total.get("failures") or total.get("unexpected_success"):
                raise TempestBenchmarkFailure([
                    test["name"] for test in six.itervalues(results.tests)
                    if test["status"] in ("fail", "uxsuccess")])
        else:
            raise TempestBenchmarkFailure(_("No information"))

    return inner_func
