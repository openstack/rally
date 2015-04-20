..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_6_discovering_more_benchmark_scenarios:

Step 6. Discovering more benchmark scenarios in Rally
=====================================================

Scenarios in the Rally repository
---------------------------------

Rally currently comes with a great collection of benchmark scenarios that use the API of different OpenStack projects like **Keystone**, **Nova**, **Cinder**, **Glance** and so on. The good news is that you can combine multiple benchmark scenarios in one task to benchmark your cloud in a comprehensive way.

First, let's see what scenarios are available in Rally. One of the ways to discover these scenario is just to inspect their `source code <https://github.com/openstack/rally/tree/master/rally/benchmark/scenarios>`_.

Rally built-in search engine
----------------------------

A much more convenient way to learn about different benchmark scenarios in Rally, however, is to use a special **search engine** embedded into its Command-Line Interface, which, for a given **search query**, prints documentation for the corresponding benchmark scenario (and also supports other Rally entities like SLA).

To search for some specific benchmark scenario by its name or by its group, use the **rally info find <query>** command:

.. code-block:: none

    $ rally info find create_meter_and_get_stats
    --------------------------------------------------------------------------------
     CeilometerStats.create_meter_and_get_stats (benchmark scenario)
    --------------------------------------------------------------------------------

    Create a meter and fetch its statistics.

    Meter is first created and then statistics is fetched for the same
    using GET /v2/meters/(meter_name)/statistics.

    Parameters:
        - kwargs: contains optional arguments to create a meter

    $ rally info find some_non_existing_benchmark
    Failed to find any docs for query: 'some_non_existing_benchmark'

You can also get the list of different benchmark scenario groups available in Rally by typing **rally info BenchmarkScenarios** command:

.. code-block:: none

    $ rally info BenchmarkScenarios
    --------------------------------------------------------------------------------
     Rally - Benchmark scenarios
    --------------------------------------------------------------------------------

    Benchmark scenarios are what Rally actually uses to test the performance of an OpenStack deployment.
    Each Benchmark scenario implements a sequence of atomic operations (server calls) to simulate
    interesing user/operator/client activity in some typical use case, usually that of a specific OpenStack
    project. Iterative execution of this sequence produces some kind of load on the target cloud.
    Benchmark scenarios play the role of building blocks in benchmark task configuration files.

    Scenarios in Rally are put together in groups. Each scenario group is concentrated on some specific
    OpenStack functionality. For example, the "NovaServers" scenario group contains scenarios that employ
    several basic operations available in Nova.

     List of Benchmark scenario groups:
    --------------------------------------------------------------------------------------------
     Name                       Description
    --------------------------------------------------------------------------------------------
     Authenticate               Benchmark scenarios for the authentication mechanism.
     CeilometerAlarms           Benchmark scenarios for Ceilometer Alarms API.
     CeilometerMeters           Benchmark scenarios for Ceilometer Meters API.
     CeilometerQueries          Benchmark scenarios for Ceilometer Queries API.
     CeilometerResource         Benchmark scenarios for Ceilometer Resource API.
     CeilometerStats            Benchmark scenarios for Ceilometer Stats API.
     CinderVolumes              Benchmark scenarios for Cinder Volumes.
     DesignateBasic             Basic benchmark scenarios for Designate.
     Dummy                      Dummy benchmarks for testing Rally benchmark engine at scale.
     GlanceImages               Benchmark scenarios for Glance images.
     HeatStacks                 Benchmark scenarios for Heat stacks.
     KeystoneBasic              Basic benchmark scenarios for Keystone.
     NeutronNetworks            Benchmark scenarios for Neutron.
     NovaSecGroup               Benchmark scenarios for Nova security groups.
     NovaServers                Benchmark scenarios for Nova servers.
     Quotas                     Benchmark scenarios for quotas.
     Requests                   Benchmark scenarios for HTTP requests.
     SaharaClusters             Benchmark scenarios for Sahara clusters.
     SaharaJob                  Benchmark scenarios for Sahara jobs.
     SaharaNodeGroupTemplates   Benchmark scenarios for Sahara node group templates.
     TempestScenario            Benchmark scenarios that launch Tempest tests.
     VMTasks                    Benchmark scenarios that are to be run inside VM instances.
     ZaqarBasic                 Benchmark scenarios for Zaqar.
    --------------------------------------------------------------------------------------------

    To get information about benchmark scenarios inside each scenario group, run:
      $ rally info find <ScenarioGroupName>
