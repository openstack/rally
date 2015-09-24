===================================================================================
4x performance increase in Keystone inside Apache using the token creation benchmark
===================================================================================

*(Contributed by Neependra Khare, Red Hat)*

Below we describe how we were able to get and verify a 4x better performance of Keystone inside Apache. To do that, we ran a Keystone token creation benchmark with Rally under different load (this benchmark scenario essentially just authenticate users with keystone to get tokens).

Goal
----
- Get the data about performance of token creation under different load.
- Ensure that keystone with increased public_workers/admin_workers values and under Apache works better than the default setup.

Summary
-------
- As the concurrency increases, time to authenticate the user gets up.
- Keystone is CPU bound process and by default only one thread of keystone-all process get started. We can increase the parallelism by:
    1. increasing public_workers/admin_workers values in keystone.conf file
    2. running keystone inside Apache
- We configured Keystone with 4 public_workers and ran Keystone inside Apache. In both cases we got upto 4x better performance as compared to default keystone configuration.

Setup
-----
Server : Dell PowerEdge R610

CPU make and model : Intel(R) Xeon(R) CPU X5650  @ 2.67GHz

CPU count: 24

RAM : 48 GB

Devstack - Commit#d65f7a2858fb047b20470e8fa62ddaede2787a85

Keystone - Commit#455d50e8ae360c2a7598a61d87d9d341e5d9d3ed

Keystone API - 2

To increase public_workers - Uncomment line with public_workers and set public_workers to 4. Then restart keystone service.

To run keystone inside Apache - Added *APACHE_ENABLED_SERVICES=key* in localrc file while setting up OpenStack environment with devstack.


Results
-------

1. Concurrency = 4

.. code-block:: json

    {'context': {'users': {'concurrent': 30,
                           'tenants': 12,
                           'users_per_tenant': 512}},
                           'runner': {'concurrency': 4, 'times': 10000, 'type': 'constant'}}


+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|public_workers|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.537     | 0.998     | 4.553     | 1.233         | 1.391         | 100.0%  | 10000 |           N           |      1       |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.189     | 0.296     | 5.099     | 0.417         | 0.474         | 100.0%  | 10000 |           N           |      4       |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.208     | 0.299     | 3.228     | 0.437         | 0.485         | 100.0%  | 10000 |           Y           |      NA      |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+


2. Concurrency = 16

.. code-block:: json

    {'context': {'users': {'concurrent': 30,
                           'tenants': 12,
                           'users_per_tenant': 512}},
                           'runner': {'concurrency': 16, 'times': 10000, 'type': 'constant'}}

+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|public_workers|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 1.036     | 3.905     | 11.254    | 5.258         | 5.700         | 100.0%  | 10000 |           N           |      1       |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.187     | 1.012     | 5.894     | 1.61          | 1.856         | 100.0%  | 10000 |           N           |      4       |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.515     | 0.970     | 2.076     | 1.113         | 1.192         | 100.0%  | 10000 |           Y           |      NA      |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+


3. Concurrency = 32

.. code-block:: json

    {'context': {'users': {'concurrent': 30,
                           'tenants': 12,
                           'users_per_tenant': 512}},
                           'runner': {'concurrency': 32, 'times': 10000, 'type': 'constant'}}

+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|public_workers|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 1.493     | 7.752     | 16.007    | 10.428        | 11.183        | 100.0%  | 10000 |           N           |       1      |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 0.198     | 1.967     | 8.54      | 3.223         | 3.701         | 100.0%  | 10000 |           N           |       4      |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
| total  | 1.115     | 1.986     | 6.224     | 2.133         | 2.244         | 100.0%  | 10000 |           Y           |       NA     |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+--------------+
