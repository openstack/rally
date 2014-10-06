===============
Rally Gate Jobs
===============

For each patch submitted for review on Gerrit, there is a set of tests called **gate jobs** to be run against it. These tests check whether the Rally code works correctly after applying the patch and provide additional guarantees that it won't break the software when it gets merged. Rally gate jobs contain tests checking the codestyle (via *pep8*), unit tests suites, functional tests and a set of Rally benchmark tasks that are executed against a real *devstack* deployment.


rally-gate.sh
-------------
This script runs a set of real Rally benchmark tasks and fetches their results in textual / visualized form (available via a special html page by clicking the corresponding job title in Gerrit). It checks that scenarios don't fail while being executed against a devstack deployment and also tests SLA criteria to ensure that benchmark tasks have completed successfully.


rally-integrated.sh
-------------------
This script runs a functional tests suite for Rally CLI. The tests call a range of Rally CLI commands and check that their output contains the expected data.
