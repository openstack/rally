============================
Launch Specific Benchmark(s)
============================


Use case
--------

A developer is working on a feature that is covered by one or more specific
benchmarks/scenarios.  He/she would like to execute a rally task with an
existing task template file (yaml or json) indicating exactly which
benchmark(s) will be executed.


Problem description
-------------------

When executing a task with a template file in Rally, all benchmarks are
executed without the ability to specify one or a set of benchmarks the user
would like to execute.


Possible solution
-----------------

* Add optional flag to rally task start command to specify one or more
benchmarks to execute as part of that test run.