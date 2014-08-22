===========================
Distributed load generation
===========================

Use Case
--------

Some OpenStack projects (Marconi, MagnetoDB) require a real huge load,
like 10-100k request per second for benchmarking.

To generate such huge load Rally have to create load from different
servers.


Problem Description
-------------------

* Rally can't generate load from different servers
* Result processing can't handle big amount of data
* There is no support for chunking results