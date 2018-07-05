..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Historical background
---------------------

Tempest, OpenStack's official test suite, is a powerful tool for running a set
of functional tests against an OpenStack cluster. Tempest automatically runs
against every patch in every project of OpenStack, which lets us avoid merging
changes that break functionality.

Unfortunately, it has limited opportunities to be used, to process its results,
etc. That is why we started Verification Component initiative a long time ago
(see `a blog post
<https://www.mirantis.com/blog/rally-openstack-tempest-testing-made-simpler/>`_
for more details, but be careful as all user interface is changed completely
since that time).

What is Verification Component and why do you need it?
------------------------------------------------------

The primary goal of Rally Product is to provide a simple way to do complex
things. As for functional testing, Verification Component includes interfaces
for:

* **Managing things**. Create an isolated virtual environment and install
  verification tool there? Yes, we can do it! Clone tool from Git repositories?
  Sure! Store several versions of one tool (you know, sometimes they are
  incompatible, with different required packages and so on)? Of course!
  In general, Verification Component allows to install, upgrade, reinstall,
  configure your tool. You should not care about zillion options anymore Rally
  will discover them via cloud UX and make the configuration file for you
  automatically.
* **Launching verifiers**. Launchers of specific tools don't always contain all
  required features, Rally team tries to fix this omission. Verification
  Component supports some of them like expected failures, a list of tests to
  skip, a list of tests to launch, re-running previous verification or just
  failed tests from it and so on. Btw, all verification runs arguments are
  stored in the database.
* **Processing results**. Rally DataBase stores all `verifications
  <../overview/glossary.html#verification>`_
  and you can obtain unified (across different verifiers)
  results at any time. You can find a verification run summary there, run
  arguments which were used, error messages and etc. Comparison mechanism for
  several verifications is available too. Verification reports can be generated
  in several formats: HTML, JSON, JUnit-XML (see :ref:`verification-reports`
  for more details). Also, reports mechanism is expendable and you can write
  your own plugin for whatever system you want.
