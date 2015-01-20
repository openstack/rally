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

.. _tutorial_step_0_installation:

Step 0. Installation
====================

Installing Rally is very simple. Just execute the following commands:

.. code-block:: none

   git clone https://git.openstack.org/stackforge/rally
   ./rally/install_rally.sh

**Notes:** The installation script should be run as root or as a normal user using **sudo**. Rally requires either the Python 2.6 or the Python 2.7 version.

There are also other installation options that you can find :ref:`here <install>`.

Now that you have rally installed, you are ready to start :ref:`benchmarking OpenStack with it <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`!
