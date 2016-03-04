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

.. _main_concepts:

Main concepts of Rally
======================

Benchmark Scenarios
-------------------

Concept
^^^^^^^

The concept of **benchmark scenarios** is a central one in Rally. Benchmark scenarios are what Rally actually uses to **test the performance of an OpenStack deployment**. They also play the role of main building blocks in the configurations of benchmark tasks. Each benchmark scenario performs a small **set of atomic operations**, thus testing some **simple use case**, usually that of a specific OpenStack project. For example, the **"NovaServers"** scenario group contains scenarios that use several basic operations available in **nova**. The **"boot_and_delete_server"** benchmark scenario from that group allows to benchmark the performance of a sequence of only **two simple operations**: it first **boots** a server (with customizable parameters) and then **deletes** it.


User's view
^^^^^^^^^^^

From the user's point of view, Rally launches different benchmark scenarios while performing some benchmark task. **Benchmark task** is essentially a set of benchmark scenarios run against some OpenStack deployment in a specific (and customizable) manner by the CLI command:

.. code-block:: bash

    rally task start --task=<task_config.json>

Accordingly, the user may specify the names and parameters of benchmark scenarios to be run in **benchmark task configuration files**. A typical configuration file would have the following contents:

.. code-block:: json

    {
        "NovaServers.boot_server": [
            {
                "args": {
                    "flavor_id": 42,
                    "image_id": "73257560-c59b-4275-a1ec-ab140e5b9979"
                },
                "runner": {"times": 3},
                "context": {...}
            },
            {
                "args": {
                    "flavor_id": 1,
                    "image_id": "3ba2b5f6-8d8d-4bbe-9ce5-4be01d912679"
                },
                "runner": {"times": 3},
                "context": {...}
            }
        ],
        "CinderVolumes.create_volume": [
            {
                 "args": {
                    "size": 42
                },
                "runner": {"times": 3},
                "context": {...}
            }
        ]
    }


In this example, the task configuration file specifies two benchmarks to be run, namely **"NovaServers.boot_server"** and **"CinderVolumes.create_volume"** (benchmark name = *ScenarioClassName.method_name*). Each benchmark scenario may be started several times with different parameters. In our example, that's the case with **"NovaServers.boot_server"**, which is used to test booting servers from different images & flavors.

Note that inside each scenario configuration, the benchmark scenario is actually launched **3 times** (that is specified in the **"runner"** field). It can be specified in **"runner"** in more detail how exactly the benchmark scenario should be launched; we elaborate on that in the *"Scenario Runners"* section below.


.. _ScenariosDevelopment:

Developer's view
^^^^^^^^^^^^^^^^

From the developer's perspective, a benchmark scenario is a method marked by a **@configure** decorator and placed in a class that inherits from the base `Scenario <https://github.com/openstack/rally/blob/0.1/rally/task/scenario.py#L94>`_. There may be arbitrary many benchmark scenarios in a scenario class; each of them should be referenced to (in the task configuration file) as *ScenarioClassName.method_name*.

In a toy example below, we define a scenario class *MyScenario* with one benchmark scenario *MyScenario.scenario*. This benchmark scenario tests the performance of a sequence of 2 actions, implemented via private methods in the same class. Both methods are marked with the **@atomic_action_timer** decorator. This allows Rally to handle those actions in a special way and, after benchmarks complete, show runtime statistics not only for the whole scenarios, but for separate actions as well.

.. code-block:: python

    from rally.task import atomic
    from rally.task import scenario


    class MyScenario(scenario.Scenario):
        """My class that contains benchmark scenarios."""

        @atomic.action_timer("action_1")
        def _action_1(self, **kwargs):
            """Do something with the cloud."""

        @atomic.action_timer("action_2")
        def _action_2(self, **kwargs):
            """Do something with the cloud."""

        @scenario.configure()
        def scenario(self, **kwargs):
            self._action_1()
            self._action_2()



Scenario runners
----------------

Concept
^^^^^^^

**Scenario Runners** in Rally are entities that control the execution type and order of benchmark scenarios. They support different running **strategies for creating load on the cloud**, including simulating *concurrent requests* from different users, periodic load, gradually growing load and so on.


User's view
^^^^^^^^^^^

The user can specify which type of load on the cloud he would like to have through the **"runner"** section in the **task configuration file**:

.. code-block:: json

    {
        "NovaServers.boot_server": [
            {
                "args": {
                    "flavor_id": 42,
                    "image_id": "73257560-c59b-4275-a1ec-ab140e5b9979"
                },
                "runner": {
                    "type": "constant",
                    "times": 15,
                    "concurrency": 2
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 3
                    },
                    "quotas": {
                        "nova": {
                            "instances": 20
                        }
                    }
                }
            }
        ]
    }


The scenario running strategy is specified by its **type** and also by some type-specific parameters. Available types include:

* **constant**, for creating a constant load by running the scenario for a fixed number of **times**, possibly in parallel (that's controlled by the *"concurrency"* parameter).
* **constant_for_duration** that works exactly as **constant**, but runs the benchmark scenario until a specified number of seconds elapses (**"duration"** parameter).
* **rps**, which executes benchmark scenarios with intervals between two consecutive runs, specified in the **"rps"** field in times per second.
* **serial**, which is very useful to test new scenarios since it just runs the benchmark scenario for a fixed number of **times** in a single thread.


Also, all scenario runners can be provided (again, through the **"runner"** section in the config file) with an optional *"timeout"* parameter, which specifies the timeout for each single benchmark scenario run (in seconds).


.. _RunnersDevelopment:

Developer's view
^^^^^^^^^^^^^^^^

It is possible to extend Rally with new Scenario Runner types, if needed. Basically, each scenario runner should be implemented as a subclass of the base `ScenarioRunner <https://github.com/openstack/rally/blob/master/rally/task/runner.py>`_ class and located in the `rally.plugins.common.runners package <https://github.com/openstack/rally/tree/master/rally/plugins/common/runners>`_. The interface each scenario runner class should support is fairly easy:

.. code-block:: python

    from rally.task import runner
    from rally import consts

    class MyScenarioRunner(runner.ScenarioRunner):
        """My scenario runner."""

        # This string is what the user will have to specify in the task
        # configuration file (in "runner": {"type": ...})

        __execution_type__ = "my_scenario_runner"


        # CONFIG_SCHEMA is used to automatically validate the input
        # config of the scenario runner, passed by the user in the task
        # configuration file.

        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "properties": {
                "type": {
                    "type": "string"
                },
                "some_specific_property": {...}
            }
        }

        def _run_scenario(self, cls, method_name, ctx, args):
            """Run the scenario 'method_name' from scenario class 'cls'
            with arguments 'args', given a context 'ctx'.

            This method should return the results dictionary wrapped in
            a runner.ScenarioRunnerResult object (not plain JSON)
            """
            results = ...

            return runner.ScenarioRunnerResult(results)




Benchmark contexts
------------------

Concept
^^^^^^^

The notion of **contexts** in Rally is essentially used to define different types of **environments** in which benchmark scenarios can be launched. Those environments are usually specified by such parameters as the number of **tenants and users** that should be present in an OpenStack project, the **roles** granted to those users, extended or narrowed **quotas** and so on.


User's view
^^^^^^^^^^^

From the user's prospective, contexts in Rally are manageable via the **task configuration files**. In a typical configuration file, each benchmark scenario to be run is not only supplied by the information about its arguments and how many times it should be launched, but also with a special **"context"** section. In this section, the user may configure a number of contexts he needs his scenarios to be run within.

In the example below, the **"users" context** specifies that the *"NovaServers.boot_server"* scenario should be run from **1 tenant** having **3 users** in it. Bearing in mind that the default quota for the number of instances is 10 instances per tenant, it is also reasonable to extend it to, say, **20 instances** in the **"quotas" context**. Otherwise the scenario would eventually fail, since it tries to boot a server 15 times from a single tenant.

.. code-block:: json

    {
        "NovaServers.boot_server": [
            {
                "args": {
                    "flavor_id": 42,
                    "image_id": "73257560-c59b-4275-a1ec-ab140e5b9979"
                },
                "runner": {
                    "type": "constant",
                    "times": 15,
                    "concurrency": 2
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 3
                    },
                    "quotas": {
                        "nova": {
                            "instances": 20
                        }
                    }
                }
            }
        ]
    }


.. _ContextDevelopment:

Developer's view
^^^^^^^^^^^^^^^^

From the developer's view, contexts management is implemented via **Context classes**. Each context type that can be specified in the task configuration file corresponds to a certain subclass of the base [https://github.com/openstack/rally/blob/master/rally/task/context.py **Context**] class. Every context class should implement a fairly simple **interface**:

.. code-block:: python

    from rally.task import context
    from rally import consts

    @context.configure(name="your_context", # Corresponds to the context field name in task configuration files
                       order=100500,        # a number specifying the priority with which the context should be set up
                       hidden=False)        # True if the context cannot be configured through the input task file
    class YourContext(context.Context):
        """Yet another context class."""

        # The schema of the context configuration format
        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "additionalProperties": False,
            "properties": {
                "property_1": <SCHEMA>,
                "property_2": <SCHEMA>
            }
        }

        def __init__(self, context):
            super(YourContext, self).__init__(context)
            # Initialize the necessary stuff

        def setup(self):
            # Prepare the environment in the desired way

        def cleanup(self):
            # Cleanup the environment properly

Consequently, the algorithm of initiating the contexts can be roughly seen as follows:

.. code-block:: python

    context1 = Context1(ctx)
    context2 = Context2(ctx)
    context3 = Context3(ctx)

    context1.setup()
    context2.setup()
    context3.setup()

    <Run benchmark scenarios in the prepared environment>

    context3.cleanup()
    context2.cleanup()
    context1.cleanup()

- where the order of contexts in which they are set up depends on the value of their *order* attribute. Contexts with lower *order* have higher priority: *1xx* contexts are reserved for users-related stuff (e.g. users/tenants creation, roles assignment etc.), *2xx* - for quotas etc.

The *hidden* attribute defines whether the context should be a *hidden* one. **Hidden contexts** cannot be configured by end-users through the task configuration file as shown above, but should be specified by a benchmark scenario developer through a special *@scenario.configure(context={...})* decorator. Hidden contexts are typically needed to satisfy some specific benchmark scenario-specific needs, which don't require the end-user's attention. For example, the hidden **"cleanup" context** (:mod:`rally.plugins.openstack.context.cleanup`) is used to make generic cleanup after running benchmark. So user can't change
it configuration via task and break his cloud.

If you want to dive deeper, also see the context manager (:mod:`rally.task.context`) class that actually implements the algorithm described above.
