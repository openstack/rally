..
      Copyright 2016 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _plugins_sla_plugin:


SLA as a plugin
===============

Let's create an SLA (success criterion) plugin that checks whether the
range of the observed performance measurements does not exceed the
allowed maximum value.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *SLA* class and implement its API
(the *add_iteration(iteration)*, the *details()* method):

.. code-block:: python

    from rally.task import sla
    from rally.common.i18n import _

    @sla.configure(name="max_duration_range")
    class MaxDurationRange(sla.SLA):
        """Maximum allowed duration range in seconds."""

        CONFIG_SCHEMA = {
            "type": "number",
            "minimum": 0.0,
        }

        def __init__(self, criterion_value):
            super(MaxDurationRange, self).__init__(criterion_value)
            self._min = 0
            self._max = 0

        def add_iteration(self, iteration):
            # Skipping failed iterations (that raised exceptions)
            if iteration.get("error"):
                return self.success   # This field is defined in base class

            # Updating _min and _max values
            self._max = max(self._max, iteration["duration"])
            self._min = min(self._min, iteration["duration"])

            # Updating successfulness based on new max and min values
            self.success = self._max - self._min <= self.criterion_value
            return self.success

        def details(self):
            return (_("%s - Maximum allowed duration range: %.2f%% <= %.2f%%") %
                    (self.status(), self._max - self._min, self.criterion_value))


Usage
^^^^^

You can refer to your SLA in the benchmark task configuration files in
the same way as any other SLA:

.. code-block:: json

    {
        "Dummy.dummy": [
            {
                "args": {
                    "sleep": 0.01
                },
                "runner": {
                    "type": "constant",
                    "times": 5,
                    "concurrency": 1
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    }
                },
                "sla": {
                    "max_duration_range": 2.5
                }
            }
        ]
    }
