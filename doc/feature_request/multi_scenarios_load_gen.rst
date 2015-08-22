======================================
Using multi scenarios to generate load
======================================


Use Case
--------

Rally should be able to generate real life load. Simultaneously create load
on different components of OpenStack, e.g. simultaneously booting VM, uploading
image and listing users.


Problem Description
-------------------

At the moment Rally is able to run only 1 scenario per benchmark.
Scenario are quite specific (e.g. boot and delete VM for example) and can't
actually generate real life load.

Writing a lot of specific benchmark scenarios that will produce more real life
load will produce mess and a lot of duplication of code.


Possible solution
-----------------

* Extend Rally task benchmark configuration in such way to support passing
  multiple benchmark scenarios in single benchmark context

* Extend Rally task output format to support results of multiple scenarios in
  single benchmark separately.

* Extend rally task plot2html and rally task detailed to show results
  separately for every scenario.
