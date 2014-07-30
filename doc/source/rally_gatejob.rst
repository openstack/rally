..
      Copyright 2014 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.


.. _rally_gatejob:

Rally gates
===========

How to create custom rally-gate job
-----------------------------------


To create rally-gate job, you should create rally-scenarios directory at the root of your project.

Normally this directory contains only {projectname}.yaml, but easily can be added more scenarios and jobs.

To {projectname}.yaml was ran on gate, you need to add "rally-jobs" to "jobs" section of projects.yaml in openstack-infra/config.

For example in glance project:

modules/openstack_project/files/jenkins_job_builder/config/projects.yaml:

.. code-block:: none

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


and add check-rally-dsvm-{projectname} to modules/openstack_project/files/zuul/layout.yaml:

.. code-block:: none

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
       - check-rally-dsvm-glance


To add one more scenario and job, you need to add {scenarioname}.yaml file here, and check-rally-dsvm-{scenarioname} in projects.yaml. For example:

add rally-scenarios/myscenario.yaml to rally-scenarios directory in you project

and modules/openstack_project/files/jenkins_job_builder/config/projects.yaml:

.. code-block:: none

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
         - 'check-rally-dsvm-{name}':
           name: myscenario

and add check-rally-dsvm-myscenario to modules/openstack_project/files/zuul/layout.yaml:

.. code-block:: none

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
       - check-rally-dsvm-myscenario

