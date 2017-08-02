=======================
Launch Specific SubTask
=======================


Use case
--------

A developer is working on a feature that is covered by one or more specific
subtask.  He/she would like to execute a rally task with an
existing task template file (YAML or JSON) indicating exactly what subtask
will be executed.


Problem description
-------------------

When executing a task with a template file in Rally, all subtasks are
executed without the ability to specify one or a set of subtasks the user
would like to execute.


Possible solution
-----------------

* Add optional flag to rally task start command to specify one or more
  subtasks to execute as part of that test run.
