..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/heat/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://sphinx-doc.org/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html


====================================================
Export task and verifications into external services
====================================================

Currently Rally stores all information about executed tasks and verifications
in its database and it is also able to provide this data in JSON format or
in the form of HTML reports. There is a request for Rally to export this data
into external services (like test management system or Google Docs)
via its API.

Problem description
===================

There are many, including a lot of proprietary, test management systems
in the market available as SaaS and/or On-Premises, like TestRail, TestLink,
TestLodge etc, which objective is to manage, organize and track all testing
efforts.

Most of the systems provide an API for importing test data. The systems also
possess data model somewhat similar to Rally's one.
It usually includes (among others) models for project, test suite test case,
test plan and test execution results.

It is suggested to provide Rally users an ability to export information about
testing their environments into such test management systems in order
to integrate benchmarking via Rally into rest of their testing activities.

Since different test management systems have alike yet different API
for the purpose it is reasonable to implement this export functionality via
plugins.

Proposed change
===============

1. Implement a base class Exporter for an export plugin at
*rally/task/exporter.py*.

..code-block:: python

    class Exporter(plugin.Plugin):
        def export(self, task, connection_string):
            ...

2. Implement a CLI command of the form

..code-block:: shell

    rally task export <UUID> <CONNECTION_STRING>

3. Implement a base class VerifyExporter for an export plugin at
*rally/verify/exporter.py*.

..code-block:: python

    class VerifyExporter(plugin.Plugin):
        def export(self, verification, connection_string):
            ...

4. Implement a CLI command of the form

..code-block:: shell

    rally verify export <UUID> <CONNECTION_STRING>

Alternatives
------------

No way


Implementation
==============

Assignee(s)
-----------

Primary assignee:

rvasilets <rvasilets@mirantis.com>

Work Items
----------

- Implement plugin base class

- Implement CLI command

- Implement plugin for TestRail

Dependencies
============

None
