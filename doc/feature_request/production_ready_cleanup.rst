========================
Production read cleanups
========================

Use Case
--------

Rally should delete in any case all resources that it created during benchmark.


Problem Description
-------------------

* (implemented) Deletion rate limit

  You can kill cloud by deleting too many objects simultaneously, so deletion
  rate limit is required

* (implemented) Retry on failures

  There should be few attempts to delete resource in case of failures

* (implemented) Log resources that failed to be deleted 

  We should log warnings about all non deleted resources. This information
  should include UUID of resource, it's type and project.

* (implemented) Pluggable

  It should be simple to add new cleanups adding just plugins somewhere.

* Disaster recovery

  Rally should use special name patterns, to be able to delete resources
  in such case if something went wrong with server that is running rally. And
  you have just new instance (without old rally db) of rally on new server.

