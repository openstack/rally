==================================
Stop scenario after several errors
==================================


Use case
--------

Starting long tests on the big environments.


Problem description
-------------------

When we start a rally scenarios on the env where keystone die we get a lot of
time from timeout


Example
-------
Times in hard tests
05:25:40 rally-scenarios.cinder
05:25:40     create-and-delete-volume [4074 iterations, 15 threads]              OK  8.91
08:00:02     create-and-delete-snapshot [5238 iterations, 15 threads]            OK  17.46
08:53:20     create-and-list-volume [4074 iterations, 15 threads]                OK  3.18
12:04:14     create-snapshot-and-attach-volume [2619 iterations, 15 threads]     FAIL
14:18:44     create-and-attach-volume [2619 iterations, 15 threads]              FAIL
14:23:47 rally-scenarios.vm
14:23:47     boot_runcommand_metadata_delete [5 iterations, 5 threads]           FAIL
16:30:46 rally-scenarios.nova
16:30:46     boot_and_list_server [5820 iterations, 15 threads]                  FAIL
19:19:30     resize_server [5820 iterations, 15 threads]                         FAIL
02:51:13     boot_and_delete_server_with_secgroups [5820 iterations, 60 threads] FAIL


Times in light variant
00:38:25 rally-scenarios.cinder
00:38:25     create-and-delete-volume [14 iterations, 1 threads]                 OK  5.30
00:40:39     create-and-delete-snapshot [18 iterations, 1 threads]               OK  5.65
00:41:52     create-and-list-volume [14 iterations, 1 threads]                   OK  2.89
00:45:18     create-snapshot-and-attach-volume [9 iterations, 1 threads]         OK  17.75
00:48:54     create-and-attach-volume [9 iterations, 1 threads]                  OK  20.04
00:52:29 rally-scenarios.vm
00:52:29     boot_runcommand_metadata_delete [5 iterations, 5 threads]           OK  128.86
00:56:42 rally-scenarios.nova
00:56:42     boot_and_list_server [20 iterations, 1 threads]                     OK  6.98
01:04:48     resize_server [20 iterations, 1 threads]                            OK  22.90


In the hard test we have a lot of timeouts from keystone and a lot of time on
test execution

Possible solution
-----------------

Improve SLA check functionality to work "online". And add ability to control
execution process and stop load generation in case of sla check failures.

