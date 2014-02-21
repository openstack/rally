=====
Rally
=====

What is Rally
=============

Rally is a Benchmark-as-a-Service project for OpenStack.

Rally is intended to provide the community with a benchmarking tool that is capable of performing **specific**, **complicated** and **reproducible** test cases on **real deployment** scenarios.

If you are here, you are probably familiar with OpenStack and know that it's really huge ecosystem of cooperative services. When something fails, performs slowly or doesn't scale it's really hard to answer on questions "why", "what" and "where"? Another reason why you could be here is that you would like to build an OpenStack CI/CD system that will allow you to improve SLA, performance and stability of OpenStack continuously.

The OpenStack QA team mostly works on CI/CD that ensures that new patches don't break specific single node installation of OpenStack. On the other hand it's clear that such CI/CD is only an indication and does not cover all cases (e.g. if cloud works well on single node installation it doesn't mean that it will work good as well on 1k servers installation under high load).. Rally aims to fix this and help us to get answer on question "How OpenStack works at scale". To make it possible we are going to automate and unify all steps that are required for benchmarking OpenStack at scale: multi node OS deployment, verification, benchmarking & profiling.


**Rally** can visualized with the help of following diagram

.. image:: https://wiki.openstack.org/w/images/e/ee/Rally-Actions.png
   :width: 700px
   :alt: Rally Architecture


Architecture
------------

Rally is split into 4 main components:

1. **Deployment Engine**, which is responsible for processing and deploying VM images (using DevStack or FUEL according to user’s preferences). The engine can do one of the following:

    + deploy an Operating System (OS) on already existing VMs;
    + starting VMs from a VM image with pre-installed OS and OpenStack;
    + delpoying multiple VMs inside each OpenStack compute node based on a VM image.
2. **VM Provider**, which interacts with cloud provider-specific interfaces to load and destroy VM images;
3. **Benchmarking Tool**, which carries out the benchmarking process in several stages:

    + runs *Tempest* tests, reduced to 5-minute length (to save the usually expensive computing time);
    + runs the user-defined test scenarios (using the Rally testing framework);
    + collects all the test results and processes the by *Zipkin* tracer;
    + puts together a benchmarking report and stores it on the machine Rally was lauched on.
4. **Orchestrator**, which is the central component of the system. It uses the Deployment Engine, to run control and compute nodes, in addition to launching an OpenStack distribution. After that, it calls the Benchmarking Tool to start the benchmarking process.


Use Cases
---------

Before diving deep in Rally architecture let's take a look at 3 major high level Rally Use Cases:

.. image:: https://wiki.openstack.org/w/images/6/6e/Rally-UseCases.png
   :width: 700px
   :alt: Rally Use Cases


Typical cases where Rally aims to help are:

- Automate measuring & profiling focused on how new code changes affect OS performance.
- Using Rally profiler to detect scaling & performance issues.
- Investigate how different deployments affect OS performance:
	- Find the set of good OpenStack deployment architectures,
	- Create deployment specifications for different loads (amount of controllers, swift nodes, etc.).
- Automate search for hardware best suited for particular OpenStack cloud.
- Automate production cloud specification generation:
	- Determine terminal loads for basic cloud operations: VM start & stop, Block Device create/destroy & various OpenStack API methods.
	- Check performance of basic cloud operations in case of different loads.


Links
----------------------

Wiki page:

    https://wiki.openstack.org/wiki/Rally

Launchpad page:

    https://launchpad.net/rally

Code is hosted on github:

    https://github.com/stackforge/rally

Rally/HowTo:

    https://wiki.openstack.org/wiki/Rally


