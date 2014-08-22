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

* Drop admin requirements
* Add way to pass already existing users
