..
      Copyright 2014 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _plugins:

Scenarios Plugins
=================

Rally provides an opportunity to create and use a custom benchmark scenario as
a plugin. The plugins mechanism can be used to simplify some experiments with
new scenarios and to facilitate their creation by users who don't want to edit
the actual Rally code.

Placement
---------

Put the plugin into the **/etc/rally/plugins/scenarios** or
**~/.rally/plugins/scenarios** directory and it will be autoloaded (they are
not created automatically, you should create them by hand). The corresponding
module should have ".py" extension.

Creation
--------

Inherit a class containing the scenario method(s) from
`rally.benchmark.scenarios.base.Scenario` or its subclasses.
Place every atomic action in separate function and wrap it with decorator
**atomic_action_timer** from `rally.benchmark.scenarios.utils`. Pass
action name as a string argument to decorator. This name should be unique for
every atomic action. It also will be used to show and store results.
Combine atomic actions into your benchmark method and wrap it with the
**scenario** decorator from `rally.benchmark.scenarios.base`.

Sample
~~~~~~
You can run this sample to test whether the plugin has been loaded and
benchmark scenario results have been stored correctly.

::

    import random
    import time

    from rally.benchmark.scenarios import base
    from rally.benchmark.scenarios import utils as scenario_utils


    class PluginClass(base.Scenario):

        @scenario_utils.atomic_action_timer("test1")
        def _test1(self, factor):
            time.sleep(random.random() * factor)

        @scenario_utils.atomic_action_timer("test2")
        def _test2(self, factor):
            time.sleep(random.random() * factor * 10)

        @base.scenario()
        def testplugin(self, factor=1):
            self._test1(factor)
            self._test2(factor)

Usage
-----

Specify the class and the benchmark method of your plugin at the top level of
the benchmark task configuration file.
If you need to pass some arguments to the benchmark method, place it in the
**args** section of the task configuration file.

Sample
~~~~~~

::

    {
        "PluginClass.testplugin": [
            {
                "args": {
                    "factor": 2
                },
                "runner": {
                    "type": "constant",
                    "times": 3,
                    "concurrency": 1
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    }
                }
            }
        ]
    }
