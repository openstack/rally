===============================================
Support benchmarking clouds that are using LDAP
===============================================

Use Case
--------

A lot of production clouds are using LDAP with read only access. It means
that load can be generated only by existing in system users and there is no admin access.


Problem Description
-------------------

Rally is using admin access to create temporary users that will be used to
produce load.


Possible Solution
-----------------

* Add some way to pass already existing users


Current Solution
----------------

* Allow the user to specify existing users in the configuration of the *ExistingCloud* deployment plugin
* When such an *ExistingCloud* deployment is active, and the benchmark task file does not specify the *"users"* context, use the existing users instead of creating the temporary ones.
* Modify the *rally show ...* commands to list resources for each user separately.
