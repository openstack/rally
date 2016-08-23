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

=======================================
Improvements for scenario output format
=======================================

Current implementation of how scenario saves output data is limited and
does not meet the needs - it neither allows having more than one data set,
nor saving custom data structures by each iteration. There is simply a dict
with int values.

This specification proposes how this can be significantly improved.

Problem description
===================

At first, let's clarify types of desired output.

Output divides on two main types: additive and complete.

*Additive output* requires processing and representation for the whole
scenario. For example each iteration has duration - this additive data can
be taken from each iteration and analyzed how it changes during the
scenario execution.

*Complete output* data is completely created by iteration and does not require
extra processing. It is related to this specific iteration only.

Currently scenario can just return a single dict with int values - this is an
additive data only, and it is stored in iteration results according to
this schema:

.. code-block::

  "result": {
      ...
      "scenario_output": {
          "type": "object",
          "properties": {
              "data": {
                  "type": "object"
              },
              "errors": {
                  "type": "string"
              },
          },
         "required": ["data", "errors"]
      }
  }

Here are main issues:

  * single data set - this does not allow to split data (if required) among
    different sources. For example scenario runs two (or more) third-party
    tools or scripts but has to put all data into single dict

  * output is additive only - so its representation makes sense only after
    putting data from all iterations together. Scenario iteration can not
    save its own data list that can be processed independently from another
    iterations.

  * there is no specific data for HTML report generation like chart title
    and chart type, so report uses hardcoded values.

As result, HTML report can represent output by a single chart of single type:

.. code-block::

          .--------.
          | Output |
     -----'        '-----------
       Scenario output
        --------------------
       |                    |
       | SINGLE StackedArea |
       |                    |
        --------------------

Proposed change
===============

Scenario should have ability to save arbitrary number of both additive
and complete output data. This data should include titles and instructions
how to be processed and displayed in HTML report.

Here is proposed iterations results structure for output data:

.. code-block::


  "result": {
      ...
      "output": {
          "additive": [
              # Each iteration duplicates "title", "description", "chart" and
              # items keys, however this seems to be less evil than keeping
              # aggregated metadata on upper level of task results schema.
              # "chart" is required by HTML report and should be a name of
              # existent Chart subclass that is responsible for processing
              # and displaying the data
              {"title": "How some durations changes during the scenario",
               "description": "Some details explained here",
               "chart": "OutputStackedAreaChart",
               "items": [[<str key>, <float value>], ...]  # Additive data
              },
              ...  # More data if required
          ],
          "complete": [
              # Complete data from this specific iteration.
              # "widget" is required by HTML report and should be a name
              # of chart widget (see details below) that responsible for
              # displaying data. We do not need to specify "chart" here
              # because this data does not require processing - it is
              # already processed and represents a result of Chart.render()
              {"title": "Interesting data from specific iteration",
               "description": "Some details explaind here",
               "widget": "StackedArea",
               "data": [
                   [
                       <str key>,
                       [[<float X pos>, <float Y value>], ...]
                   ],
                   ...
               ]
              },
              ...  # More data if required
          ]
      }
  }

**NOTES**:

  * for backward compatibility, data from deprecated "scenario_output" should
    be transformed into "output/data/additive[0]" on-the-fly (for example
    if we load task results from file)

  * as you can see, there is no container *output/errors* - that is because
    value of *errors* is not used at all and not required (there is another
    container for errors in iteration results)

How scenario saves output data
------------------------------

Scenario should be extended with method *add_output()*:

.. code-block::

 class Scenario(...):

     def __init__(self, context=None):
         ...
         self._output = {"additive": [], "complete": []}

     ...

     def add_output(self, additive=None, complete=None):
         """Add iteration values for additive output.

         :param additive: dict with additive output
         :param complete: dict with complete output
         :raises RallyException: When additive or complete has wrong format
         """
         for key, value in (("additive", additive), ("complete", complete)):
             if value:
                 try:
                     jsonschema.validate(
                         value, task.OUTPUT_SCHEMA["properties"][key]["items"])
                     self._output[key].append(value)
                 except jsonschema.ValidationError:
                     raise exceptions.RallyException(
                         "%s output has wrong format" % key.capitalize())


Here is an example how scenario can save different output:

.. code-block::

 class SomePlugin(Scenario):

     def specific_scenario(self):
         ...

         self.add_output(additive={"title": "Foo data",
                                   "description": "Some words about Foo",
                                   "chart": "OutputStackedAreaChart",
                                   "items": [["foo 1", 12], ["foo 2", 34]]})
         self.add_output(additive={"title": "Bar data",
                                   "description": "Some words about Bar",
                                   "chart": "OutputAvgChart",
                                   "items": [["bar 1", 56], ["bar 2", 78]]})
         self.add_output(complete={"title": "Complete data",
                                   "description": "Some details here",
                                   "widget": "StackedArea",
                                   "data": [["foo key", [ ... ]], ... ]})
         self.add_output(complete={"title": "Another data",
                                   "description": "Some details here",
                                   "widget": "Pie",
                                   "data": [["bar key", [ ... ]], ... ]})
         self.add_output(complete={"title": "Yet another data",
                                   "description": "Some details here",
                                   "widget": "Table",
                                   "data": [["spam key", [ ... ]], ... ]})

Displaying scenario output in HTML report
-----------------------------------------

The following changes are planned for HTML report and charts classes:

  * rename tab *Output* to *Scenario Data*
  * implement subtabs under *Scenario Data*: *Aggregated* and *Per iteration*
  * *Aggregated* subtab shows charts with additive data
  * *Per iteration* subtab shows charts with complete data, for each iteration
  * Both subtabs (as well as parent tab) are shown only if there is
    something to display
  * add base class OutputChart and generic charts classes for processing
    output data: OutputStackedAreaChart, OutputAvgChart, OutputStatsTable
  * add optional *title* and *description* arguments to OutputChart.__init__()
    so title and description - this is important for custom charts
  * add *WIDGET* property to each OutputChart subclass to bind it to specific
    chart widget (StackedArea, Pie, Table). For example, AvgChart will be
    bound to "Pie". This will allow defining both how to process and how
    to display some data simply by single class name
  * update return value format of OutputChart.render() with title and widget:
    {"title": <str>, "description": <str>, "widget": <str>, "data": [...]}

UI sketch for active "Aggregated" subtab:

.. code-block::

         .---------------.
         | Scenario Data |
     ----'               '-------------------
       Aggregated   Per iteration
                    -------------
       <Custom chart title>
       <Here is a description text>
        ----------------------------
       |                            |
       | Any available chart widget |
       |                            |
        ----------------------------

       <Custom chart title>
       <Here is a description text>
        ----------------------------
       |                            |
       | Any available chart widget |
       |                            |
        ----------------------------

       [... more charts]

UI sketch for active "Per iteration" subtab, let it be iteration 5
selected by dropdown:

.. code-block::

         .---------------.
         | Scenario Data |
     ----'               '-------------------
       Aggregated   Per iteration
       ----------

       [iteration 5]

       <Custom chart title>
       <Here is a description text>
        ----------------------------
       |                            |
       | Any available chart widget |
       |                            |
        ----------------------------

       <Custom chart title>
       <Here is a description text>
        ----------------------------
       |                            |
       | Any available chart widget |
       |                            |
        ----------------------------

       [... more charts]

Alternatives
------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  * amaretskiy <amaretskiy@mirantis.com>

Work Items
----------

  * Update task results schema with *output* container
  * Extend Scenario with method *add_output()*
  * Bound Chart subclasses to specific charts widgets
  * Add generic Charts subclasses for output data
  * Changes in HTML report related to *Output* tab
  * Add scenario with example output data

Dependencies
============

None
