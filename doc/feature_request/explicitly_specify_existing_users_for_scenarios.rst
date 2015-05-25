===============================================
Explicitly specify existing users for scenarios
===============================================


Use Case
--------

Rally allows to reuse existing users for scenario runs. And we should be able
to use only specified set of existing users for specific scenarios.


Problem Description
-------------------

For the moment if used `deployment` with existing users then Rally chooses
user for each scenario run randomly. But there are cases when we may want
to use one scenario with one user and another with different one specific user.
Main reason for it is in different set of resources that each user has and
those resources may be required for scenarios. Without this feature Rally user
is forced to make all existing users similar and have all required resources
set up for all scenarios he uses. But it is redundant.


Possible solution
-----------------

* Make it possible to use explicitly existing_users context
