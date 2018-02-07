..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/rally/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

=================================
OSProfiler integration into Rally
=================================

The OSProfiler is a distributed trace toolkit library. It provides pythonic
helpers to do trace generation to avoid repeated code to trace WSGI, RPC, DB,
and other important places...

Integration OSProfiler into Rally can help to dig into concurrency problems of
OpenStack which is a huge ecosystem of cooperative services.

Problem description
===================

Rally Framework provides a powerful interface to generate real, big, load for
the deployment. Such load can kill the cloud, specifically OpenStack. There is
no way to identify reasons and bottlenecks without parsing timestamps and logs.
To fix that issue embedding profiling into each of workload iteration can help
to display wide picture of where we were in that particular moment when
something went wrong.

Proposed change
===============

Two facts about OSProfiler which are the start point for the proposed changes:

* HMAC key is used as a secret identifier while profiling
* Initialization of profiling is made in thread safe mode. Profiling of one
  iteration should not influence profiling another one

Storing secret key
------------------

The HMAC key is not something that will be changed from one task to another.
It is specific thing for the deployment, like authentication url or other
credentials. That is why Rally deployment config is the best place to store
such information.

Since OSProfiler is OpenStack specific tool, we need to extend OpenStack
credentials model in Rally to support new argument. It should be done in two
places: validation (by modifying jsonschema [0]_) and the place where
credentials are store (specific class [1]_ [2]_).

Initialization profiling
------------------------

As it was mentioned before, we need to initialize OSProfiler per iteration.
OSProfiler is made in thread safe mode [3]_, so we should not have problem from
that side.

Initialization of OSProfiler is quite simple.

  .. code-block:: python

    from osprofiler import profiler

    profiler.init(HMAC_KEY)


As for the place where to initialize OSProfiler in Rally, constructor of
scenario is a good choice. First of all, we have a separate class for OpenStack
scenarios [4]_ which means that integration with OSProfiler there will not
affect all other platforms. Another reason for using constructor is that we
initialize new instance of scenario class for each iterations.

Storing profiling results
-------------------------

OSProfiler sends to collector a message at every trace point. We should not
care about supported OSProfiler backends and use only OSProfiler as
entry-point.

The full trace can be obtained via trace-id after profiling is initialized.

  .. code-block:: python

    from osprofiler import profiler

    trace_id = profiler.get().get_base_id()

At the first step of integration OSProfiler in Rally, let's store that trace-id
just like simple text. It will allow to show trace-id in Rally HTML and JSON
reports.

  .. code-block:: python

    self.add_output(complete={"title": "OSProfiler Trace-ID",
                              "chart_plugin": "TextArea",
                              "data": [trace_id]})

We can execute these lines in the same place where we initialize OSProfiler.

In future, we should develop a separate chart that will embed OSProfiler html
report as a separate tab in the Rally report.

Enabling profiling
------------------

Enabling/disabling profiling should be done via rally configuration file:

* It is common place for storing different kinds of options.
* There is planned feature that will able to re-set config options via
  deployment config or task file.

The default value of that options should be True. In case of missing HMAC key
in credentials, attempt to initialize OSProfiler should not be started.

Alternatives
------------

Here [5]_ you can find the answer to that section.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Andrey Kurilin <andr.kurilin@gmail.com>


Work Items
----------

* Extend OpenStack credentials
* Add new configuration option to Rally
* Extend OpenStack scenario base class to initialize OSProfiler and store
  trace id


Dependencies
============

None


References
==========

.. [0] https://github.com/openstack/rally/blob/a5691d7850b5abd7ea707730f0d48d75116d88d3/rally/plugins/openstack/credential.py#L154
.. [1] https://github.com/openstack/rally/blob/a5691d7850b5abd7ea707730f0d48d75116d88d3/rally/plugins/openstack/credential.py#L26
.. [2] https://github.com/openstack/rally/blob/a5691d7850b5abd7ea707730f0d48d75116d88d3/rally/plugins/openstack/credential.py#L161
.. [3] https://github.com/openstack/osprofiler/blob/1.8.0/osprofiler/profiler.py#L29-L30
.. [4] https://github.com/openstack/rally/blob/a5691d7850b5abd7ea707730f0d48d75116d88d3/rally/plugins/openstack/scenario.py#L28-L55
.. [5] https://docs.openstack.org/osprofiler/latest/user/background.html#why-not-cprofile-and-etc
