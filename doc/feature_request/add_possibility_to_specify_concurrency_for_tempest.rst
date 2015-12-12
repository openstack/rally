========================================
Running Tempest using custom concurrency
========================================


Use case
--------

User might want to use specific concurrency for running tests based on his
deployment and available resources.


Problem description
-------------------

"rally verify start" command does not allow to specify concurrency
for tempest tests. And they always run using concurrency equal
to amount of CPU cores.


Possible solution
-----------------

* Add ``--concurrency`` option to "rally verify start" command.
