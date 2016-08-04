..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
SLA Performance degradation plugin
==================================

Problem description
===================

During density and reliability testing of OpenStack with Rally
we observed test cases, during execution of which performance
of OpenStack cluster has been drammatically degradated.

Proposed change
===============

Develop a new Rally SLA plugin: *performance_degradation*

This SLA plugin should find minimum and maximum duration of
iterations completed without errors during Rally task execution.
Assuming that minimum duration is 100%, it should calculate
performance degradation against maximum duration.

SLA plugin results:
  - failure if performance degradation is more than value set
  in plugin's max_degradation parameter;
  - success if degradation is less
  - performance degradation value as a percentage.

How to enable this plugin:

.. code:: json

    "sla": {
        "performance_degradation": {
            "max_degradation": 50
            }
    }

Alternatives
------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:

anevenchannyy <anevenchannyy@mirantis.com>

Work Items
----------

 - Implement plugin
 - Add non-voting job with this plugin to the most important OpenStack services

Dependencies
============

None
