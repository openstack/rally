===============
Rally Gate Jobs
===============

For each patch submitted for review on Gerrit, there is a set of tests called **gate jobs** to be run against it. These tests check whether the Rally code works correctly after applying the patch and provide additional guarantees that it won't break the software when it gets merged. Rally gate jobs contain tests checking the codestyle (via *pep8*), unit tests suites, functional tests and a set of Rally benchmark tasks that are executed against a real *devstack* deployment.


rally-gate.sh
-------------
This script runs a set of real Rally benchmark tasks and fetches their results in textual / visualized form (available via a special html page by clicking the corresponding job title in Gerrit). It checks that scenarios don't fail while being executed against a devstack deployment and also tests SLA criteria to ensure that benchmark tasks have completed successfully.


rally-integrated.sh
-------------------
This script runs a functional tests suite for Rally CLI. The tests call a range of Rally CLI commands and check that their output contains the expected data.


rally-verify.sh
---------------
This script runs various "rally verify" commands. This set of commands allow us to perform Tempest tests of OpenStack live cloud and display verification results.
The verification results obtained by running various "rally verify <cmd>" commands including "start", "show", "list" are compared using the "rally verify results" command, which are then saved in csv, html and json formats in the "rally-verify" directory.
Jenkins uses this script by running the 'gate-rally-dsvm-verify' job.


test_install.sh
---------------
This script tests the correct working of the install_rally.sh, used for the installation of Rally. Jenkins tests this script by running it against Centos6 and Ubuntu 12.04 in the corresponding jobs 'gate-rally-install-bare-centos6' and 'gate-rally-install-bare-precise'.


Jenkins
-------
Jenkins is a Continuous Integration system which works as the scheduler. It receives events related to proposed changes, triggers tests based on those events, and reports back.
For each patch that is uploaded for review on Gerrit, Jenkins runs it against the various rally gate jobs listed below along with their functions and local equivalents:

* gate-rally-pep8                    : code style check (equal to tox -epep8)
* gate-rally-docs                    : documention generation (equal to tox -edocs)
* gate-rally-python27                : unit tests against python27 (equal to tox -epy27)
* gate-rally-python34(non-voting)    : unit tests against python34 ( equal to tox -epy34) (non-voting since not all tests pass this)
* rally-coverage                     : generates unit test coverage (equal to tox -cover)
* gate-rally-install-bare-centos6    : testing of test_install.sh(described above) against Centos
* gate-rally-install-bare-precise    : testing of test_install.sh(described above) against Ubuntu 10.04
* gate-rally-dsvm-rally              : runs rally-gate.sh(described above) against OpenStack deployed by devstack with nova-network (It is standard dsvm job)
* gate-rally-dsvm-neutron-rally      : runs rally-gate.sh against OpenStack deployed by devastack with neutron
* gate-rally-dsvm-cli                : runs rally-integrated.sh ( equal to tox -ecli)
* gate-rally-dsvm-verify(non-voting) : runs rally-verify.sh and tests Rally and Tempest integration in all possible ways
* gate-rally-tox-self(non-voting)    : not yet used

 and a success in these tests(except non-voting) would mean that the patch is approved by Jenkins.
