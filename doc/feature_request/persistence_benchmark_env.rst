===========================================
Add support of persistence task environment
===========================================

Use Case
--------

There are situations when same environment is used across different tasks.
For example you would like to improve operation of listing objects.
For example:

- Create hundreds of objects
- Collect baseline of list performance
- Fix something in system
- Repeat the performance test
- Repeat fixing and testing until things are fixed.

Current implementation of Rally will force you to recreate task context which
is time consuming operation.


Problem Description
-------------------

Fortunately Rally has already a mechanism for creating task environment via
contexts. Unfortunately it's atomic operation:
- Create task context
- Perform subtask scenario-runner pairs
- Destroy task context

This should be split to 3 separated steps.


Possible solution
-----------------

* Add new CLI operations to work with task environment:
  (show, create, delete, list)

* Allow task to start against existing task context (instead of deployment)
