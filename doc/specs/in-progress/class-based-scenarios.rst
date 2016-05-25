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


===================================
Class-based Scenario Implementation
===================================

Introduce scenarios implementation as classes, not methods.

Problem description
===================

Current scenario implementation transforms method to class at runtime,
so this overcomplicates the code.

Method-based extensions mechanism is not a common practice in frameworks,
so this is a bit confusing.

Most Rally plugins like Context, SLA, Runner, OutputChart (except Scenario)
are implemented as classes, not methods.

Proposed change
===============

Add an ability to implement scenarios as classes, keeping full backward
compatibility with existing code.

This means that class represents single scenario which is actually implemented
in method *Scenario.run()*.

So input task can contain scenario names that does not have method part
splitted by dot from class part.

For example, here we have two scenarios, first one is in old manner
and another is class-based:

.. code-block:: json

 {
   "Dummy.dummy": [
     {
       "runner": {
         "type": "serial",
         "times": 20
       }
     }
   ],
   "another_dummy_scenario": [
     {
       "runner": {
         "type": "serial",
         "times": 20
       }
     }
   ]
 }

Class AnotherDummyScenario should have method run():

.. code-block:: python

  from rally.task import scenario

  @scenario.configure(name="another_dummy_scenario")
  class AnotherDummyScenario(scenario.Scenario):

      def run(self):
          """Scenario implementation."""

Modules *rally.task.engine* and *rally.task.processing* should be modified to
make them working with class-based scenarios.

Alternatives
------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:

  Alexander Maretskiy <amaretskiy@mirantis.com>


Work Items
----------

 - Update task.engine and task.processing for class-based scenarios
 - Transform all Dummy scenarios into class-based implementations as first
   stage of usage class-based scenarios.

Dependencies
============

None
