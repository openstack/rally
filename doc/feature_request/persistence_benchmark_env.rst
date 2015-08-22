================================================
Add support of persistence benchmark environment
================================================

Use Case
--------

To benchmark many of operations like show, list, detailed you need to have
already these resource in cloud. So it will be nice to be able to create
benchmark environment once before benchmarking. So run some amount of
benchmarks that are using it and at the end just delete all created resources
by benchmark environment.


Problem Description
-------------------

Fortunately Rally has already a mechanism for creating benchmark environment,
that is used to create load. Unfortunately it's atomic operation:
(create environment, make load, delete environment).
This should be split to 3 separated steps.


Possible solution
-----------------

* Add new CLI operations to work with benchmark environment:
  (show, create, delete, list)

* Allow task to start against benchmark environment (instead of deployment)
