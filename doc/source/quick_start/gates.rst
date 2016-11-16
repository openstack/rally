..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _gates:

Rally OpenStack Gates
=====================

Gate jobs
---------

The **OpenStack CI system** uses the so-called **"Gate jobs"** to control
merges of patches submitted for review on Gerrit. These **Gate jobs** usually
just launch a set of tests -- unit, functional, integration, style -- that
check that the proposed patch does not break the software and can be merged
into the target branch, thus providing additional guarantees for the stability
of the software.


Create a custom Rally Gate job
------------------------------

You can create a **Rally Gate job** for your project to run Rally benchmarks
against the patchsets proposed to be merged into your project.

To create a rally-gate job, you should create a **rally-jobs/** directory at
the root of your project.

As a rule, this directory contains only **{projectname}.yaml**, but more
scenarios and jobs can be added as well. This yaml file is in fact an input
Rally task file specifying benchmark scenarios that should be run in your gate
job.

To make *{projectname}.yaml* run in gates, you need to add *"rally-jobs"* to
the "jobs" section of *projects.yaml* in *openstack-infra/project-config*.


Example: Rally Gate job for Glance
----------------------------------

Let's take a look at an example for the `Glance`_ project:

Edit *jenkins/jobs/projects.yaml:*

.. parsed-literal::

   - project:
       name: glance
       node: 'bare-precise || bare-trusty'
       tarball-site: tarballs.openstack.org
       doc-publisher-site: docs.openstack.org

       jobs:
         - python-jobs
         - python-icehouse-bitrot-jobs
         - python-juno-bitrot-jobs
         - openstack-publish-jobs
         - translation-jobs
         **- rally-jobs**


Also add *gate-rally-dsvm-{projectname}* to *zuul/layout.yaml*:

.. parsed-literal::

   - name: openstack/glance
     template:
       - name: merge-check
       - name: python26-jobs
       - name: python-jobs
       - name: openstack-server-publish-jobs
       - name: openstack-server-release-jobs
       - name: periodic-icehouse
       - name: periodic-juno
       - name: check-requirements
       - name: integrated-gate
       - name: translation-jobs
       - name: large-ops
       - name: experimental-tripleo-jobs
     check:
       - check-devstack-dsvm-cells
       **- gate-rally-dsvm-glance**
     gate:
       - gate-devstack-dsvm-cells
     experimental:
       - gate-grenade-dsvm-forward


To add one more scenario and job, you need to add *{scenarioname}.yaml* file
here, and *gate-rally-dsvm-{scenarioname}* to *projects.yaml*.

For example, you can add *myscenario.yaml* to *rally-jobs* directory in your
project and then edit *jenkins/jobs/projects.yaml* in this way:

.. parsed-literal::

   - project:
       name: glance
       github-org: openstack
       node: bare-precise
       tarball-site: tarballs.openstack.org
       doc-publisher-site: docs.openstack.org

       jobs:
         - python-jobs
         - python-havana-bitrot-jobs
         - openstack-publish-jobs
         - translation-jobs
         - rally-jobs
         **- 'gate-rally-dsvm-{name}':
           name: myscenario**

Finally, add *gate-rally-dsvm-myscenario* to *zuul/layout.yaml*:

.. parsed-literal::

   - name: openstack/glance
     template:
       - name: python-jobs
       - name: openstack-server-publish-jobs
       - name: periodic-havana
       - name: check-requirements
       - name: integrated-gate
     check:
       - check-devstack-dsvm-cells
       - check-tempest-dsvm-postgres-full
       - gate-tempest-dsvm-large-ops
       - gate-tempest-dsvm-neutron-large-ops
       **- gate-rally-dsvm-myscenario**

It is also possible to arrange your input task files as templates based on
``Jinja2``. Say, you want to set the image names used throughout the
*myscenario.yaml* task file as a variable parameter. Then, replace concrete
image names in this file with a variable:

.. code-block:: yaml

    ...

    NovaServers.boot_and_delete_server:
      -
        args:
          image:
              name: {{image_name}}
        ...

    NovaServers.boot_and_list_server:
      -
        args:
          image:
              name: {{image_name}}
        ...

and create a file named *myscenario_args.yaml* that will define the parameter
values:

.. code-block:: yaml

    ---

      image_name: "^cirros.*uec$"

this file will be automatically used by Rally to substitute the variables in
*myscenario.yaml*.


Plugins & Extras in Rally Gate jobs
-----------------------------------

Along with scenario configs in yaml, the **rally-jobs** directory can also
contain two subdirectories:

- **plugins**: :ref:`Plugins <plugins>` needed for your gate job;
- **extra**: auxiliary files like bash scripts or images.

Both subdirectories will be copied to *~/.rally/* before the job gets started.

.. references:

.. _Glance: https://wiki.openstack.org/wiki/Glance
