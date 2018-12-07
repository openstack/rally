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

.. _project_info:

Project Info and Release Notes
==============================

Maintainers
-----------

Project Team Lead (PTL)
~~~~~~~~~~~~~~~~~~~~~~~


+------------------------------+------------------------------------------------+
|       Contact                |             Area of interest                   |
+------------------------------+------------------------------------------------+
| | Andrey Kurilin             |  * Chief Architect                             |
| | andreykurilin (irc)        |  * Release management                          |
| | andreykurilin (gitter)     |  * Community management                        |
| | andr.kurilin@gmail.com     |  * Core team management                        |
| |                            |  * Road Map                                    |
+------------------------------+------------------------------------------------+

| *If you would like to refactor whole Rally or have UX/community/other
   issues please contact me.*


Project Core maintainers
~~~~~~~~~~~~~~~~~~~~~~~~

+------------------------------+------------------------------------------------+
|       Contact                |             Area of interest                   |
+------------------------------+------------------------------------------------+
| | Alexander Maretskiy        |  * Rally reports                               |
| | amaretskiy (irc)           |  * Front-end                                   |
| | amaretskiy@mirantis.com    |                                                |
+------------------------------+------------------------------------------------+
| | Anton Studenov             |  * Rally Deployment                            |
| | tohin (irc)                |  * Task Hooks                                  |
| | astudenov@mirantis.com     |                                                |
+------------------------------+------------------------------------------------+
| | Boris Pavlovic             |  * Founder and ideological leader              |
| | boris-42 (irc)             |  * Architect                                   |
| | boris@pavlovic.me          |  * Rally task & plugins                        |
+------------------------------+------------------------------------------------+
| | Chen Haibing               |  * Rally task & plugins                        |
| | chenhb-zte (gitter)        |                                                |
| | chen.haibing1@zte.com.cn   |                                                |
+------------------------------+------------------------------------------------+
| | Chris St. Pierre           |  * Rally task & plugins                        |
| | stpierre (irc)             |  * Bash guru ;)                                |
| | cstpierr@cisco.com         |                                                |
+------------------------------+------------------------------------------------+
| | Hai Shi                    |  * Rally task & plugins                        |
| | shihai1991 (gitter)        |                                                |
| | shihai1992@gmail.com       |                                                |
+------------------------------+------------------------------------------------+
| | Illia Khudoshyn            |  * Rally task & plugins                        |
| | ikhudoshyn (irc)           |                                                |
| | ikhudoshyn@mirantis.com    |                                                |
+------------------------------+------------------------------------------------+
| | Kun Huang                  |  * Rally task & plugins                        |
| | kun_huang (irc)            |                                                |
| | gareth.huang@huawei.com    |                                                |
+------------------------------+------------------------------------------------+
| | Li Yingjun                 |  * Rally task & plugins                        |
| | liyingjun (irc)            |                                                |
| | yingjun.li@kylin-cloud.com |                                                |
+------------------------------+------------------------------------------------+
| | Roman Vasilets             |  * Rally task & plugins                        |
| | rvasilets (irc)            |                                                |
| | pomeo92@gmail.com          |                                                |
+------------------------------+------------------------------------------------+
| | Sergey Skripnick           |  * Rally CI/CD                                 |
| | redixin (irc)              |  * Rally deploy                                |
| | sskripnick@mirantis.com    |  * Automation of everything                    |
+------------------------------+------------------------------------------------+
| | Yaroslav Lobankov          |  * Rally Verification                          |
| | ylobankov (irc)            |                                                |
| | ylobankov@mirantis.com     |                                                |
+------------------------------+------------------------------------------------+

| *All cores from this list are reviewing all changes that are proposed to Rally.
  To avoid duplication of efforts, please contact them before starting work on
  your code.*


Plugin Core reviewers
~~~~~~~~~~~~~~~~~~~~~

+------------------------------+------------------------------------------------+
|       Contact                |             Area of interest                   |
+------------------------------+------------------------------------------------+
| | Ivan Kolodyazhny           |  * Cinder plugins                              |
| | e0ne (irc)                 |                                                |
| | e0ne@e0ne.info             |                                                |
+------------------------------+------------------------------------------------+
| | Nikita Konovalov           |  * Sahara plugins                              |
| | NikitaKonovalov (irc)      |                                                |
| | nkonovalov@mirantis.com    |                                                |
+------------------------------+------------------------------------------------+
| | Oleg Bondarev              |  * Neutron plugins                             |
| | obondarev (irc)            |                                                |
| | obondarev@mirantis.com     |                                                |
+------------------------------+------------------------------------------------+
| | Sergey Kraynev             |  * Heat plugins                                |
| | skraynev (irc)             |                                                |
| | skraynev@mirantis.com      |                                                |
+------------------------------+------------------------------------------------+
| | Spyros Trigazis            |  * Magnum plugins                              |
| | strigazi (irc)             |                                                |
| | strigazi@gmail.com         |                                                |
+------------------------------+------------------------------------------------+



| *All cores from this list are responsible for their component plugins.
  To avoid duplication of efforts, please contact them before starting working
  on your own plugins.*


Useful links
------------
- `Source code`_
- `Rally roadmap`_
- `Project space`_
- `Bugs`_
- `Patches on review`_
- `Meeting logs`_ (server: **irc.freenode.net**, channel:
   **#openstack-meeting**)
- `IRC logs`_ (server: **irc.freenode.net**, channel: **#openstack-rally**)
- `Gitter chat`_
- `Trello board`_


Where can I discuss and propose changes?
----------------------------------------
- Our IRC channel: **#openstack-rally** on **irc.freenode.net**;
- Weekly Rally team meeting (in IRC): **#openstack-meeting** on
  **irc.freenode.net**, held on Mondays at 14:00 UTC;
- OpenStack mailing list: **openstack-discuss@lists.openstack.org** (see
  `subscription and usage instructions`_);
- `Rally team on Launchpad`_: Answers/Bugs/Blueprints.

.. _release_notes:

.. include:: release_notes.rst

.. references:

.. _Source code: https://github.com/openstack/rally
.. _Rally roadmap: https://docs.google.com/a/mirantis.com/spreadsheets/d/16DXpfbqvlzMFaqaXAcJsBzzpowb_XpymaK2aFY2gA2g/edit#gid=0
.. _Project space: https://launchpad.net/rally
.. _Bugs: https://bugs.launchpad.net/rally
.. _Patches on review: https://review.openstack.org/#/q/status:open+project:openstack/rally,n,z
.. _Meeting logs: http://eavesdrop.openstack.org/meetings/rally/2016/
.. _IRC logs: http://irclog.perlgeek.de/openstack-rally
.. _Gitter chat: https://gitter.im/rally-dev/Lobby
.. _Trello board: https://trello.com/b/DoD8aeZy/rally
.. _subscription and usage instructions: http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-dev
.. _Rally team on Launchpad: https://launchpad.net/rally
