=========
Benchmark
=========
Authenticate users with keystone to get tokens.

Goal
----
- To get data about performance of token creation under different load.
- To ensure that keystone under apache works better than the default setup that uses event-let.

Summary
-------
- As the concurrency increases, time to authenticate the user gets up.
- Running keystone inside apache gives 4x better performance for this setup. With
  the default configuration of keystone only single threaded process is launched,
  which is bottlenecked on CPU. Running keystone inside apache enables us to
  get authentication done on multiple CPUs, which gives better performance.


Setup
-----
Server : Dell PowerEdge R610

CPU make and model : Intel(R) Xeon(R) CPU X5650  @ 2.67GHz

CPU count: 24

RAM : 48 GB

Devstack - Commit#d65f7a2858fb047b20470e8fa62ddaede2787a85

Keystone - Commit#455d50e8ae360c2a7598a61d87d9d341e5d9d3ed

Keystone API - 2

To run keystone inside apache - Added *APACHE_ENABLED_SERVICES=key* in localrc file while setting up OpenStack environment with devstack.

Results
-------

1. Concurrency = 4

    {'context': {'users': {'concurrent': 30,
                         | 'tenants': 12,
                         | 'users_per_tenant': 512}},
                         | 'runner': {'concurrency': 4, 'times': 10000, 'type': 'constant'}}


+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 0.537     | 0.998     | 4.553     | 1.233         | 1.391         | 100.0%  | 10000 |           N           |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 0.208     | 0.299     | 3.228     | 0.437         | 0.485         | 100.0%  | 10000 |           Y           |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+

Graphs
  - ./authenticate/times_10000_concurrency_4_apacheEnabledKeystone_N.html
  - ./authenticate/times_10000_concurrency_4_apacheEnabledKeystone_Y.html


2. Concurrency = 16

    {'context': {'users': {'concurrent': 30,
                         | 'tenants': 12,
                         | 'users_per_tenant': 512}},
                         | 'runner': {'concurrency': 16, 'times': 10000, 'type': 'constant'}}

+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 1.036     | 3.905     | 11.254    | 5.258         | 5.700         | 100.0%  | 10000 |            N          |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 0.515     | 0.970     | 2.076     | 1.113         | 1.192         | 100.0%  | 10000 |           Y           |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+

Graphs
  - ./authenticate/times_10000_concurrency_16_apacheEnabledKeystone_N.html
  - ./authenticate/times_10000_concurrency_16_apacheEnabledKeystone_Y.html


3. Concurrency = 32

    {'context': {'users': {'concurrent': 30,
                         | 'tenants': 12,
                         | 'users_per_tenant': 512}},
                         | 'runner': {'concurrency': 32, 'times': 10000, 'type': 'constant'}}

+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| action | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |apache enabled keystone|
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 1.493     | 7.752     | 16.007    | 10.428        | 11.183        | 100.0%  | 10000 |           N           |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+
| total  | 1.115     | 1.986     | 6.224     | 2.133         | 2.244         | 100.0%  | 10000 |           Y           |
+--------+-----------+-----------+-----------+---------------+---------------+---------+-------+-----------------------+

Graphs
  - ./authenticate/times_10000_concurrency_32_apacheEnabledKeystone_N.html
  - ./authenticate/times_10000_concurrency_32_apacheEnabledKeystone_Y.html

