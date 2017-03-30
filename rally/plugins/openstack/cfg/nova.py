# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg

OPTS = {"benchmark": [
    # prepoll delay, timeout, poll interval
    # "start": (0, 300, 1)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "start",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "start"),
    cfg.FloatOpt("nova_server_%s_timeout" % "start",
                 default=float(300),
                 help="Server %s timeout" % "start"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "start",
                 default=float(1),
                 help="Server %s poll interval" % "start"),
    # "stop": (0, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "stop",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "stop"),
    cfg.FloatOpt("nova_server_%s_timeout" % "stop",
                 default=float(300),
                 help="Server %s timeout" % "stop"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "stop",
                 default=float(2),
                 help="Server %s poll interval" % "stop"),
    # "boot": (1, 300, 1)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "boot",
                 default=float(1),
                 help="Time to sleep after %s before polling"
                      " for status" % "boot"),
    cfg.FloatOpt("nova_server_%s_timeout" % "boot",
                 default=float(300),
                 help="Server %s timeout" % "boot"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "boot",
                 default=float(2),
                 help="Server %s poll interval" % "boot"),
    # "delete": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "delete",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "delete"),
    cfg.FloatOpt("nova_server_%s_timeout" % "delete",
                 default=float(300),
                 help="Server %s timeout" % "delete"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "delete",
                 default=float(2),
                 help="Server %s poll interval" % "delete"),
    # "reboot": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "reboot",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "reboot"),
    cfg.FloatOpt("nova_server_%s_timeout" % "reboot",
                 default=float(300),
                 help="Server %s timeout" % "reboot"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "reboot",
                 default=float(2),
                 help="Server %s poll interval" % "reboot"),
    # "rebuild": (1, 300, 1)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "rebuild",
                 default=float(1),
                 help="Time to sleep after %s before polling"
                      " for status" % "rebuild"),
    cfg.FloatOpt("nova_server_%s_timeout" % "rebuild",
                 default=float(300),
                 help="Server %s timeout" % "rebuild"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "rebuild",
                 default=float(1),
                 help="Server %s poll interval" % "rebuild"),
    # "rescue": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "rescue",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "rescue"),
    cfg.FloatOpt("nova_server_%s_timeout" % "rescue",
                 default=float(300),
                 help="Server %s timeout" % "rescue"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "rescue",
                 default=float(2),
                 help="Server %s poll interval" % "rescue"),
    # "unrescue": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "unrescue",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "unrescue"),
    cfg.FloatOpt("nova_server_%s_timeout" % "unrescue",
                 default=float(300),
                 help="Server %s timeout" % "unrescue"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "unrescue",
                 default=float(2),
                 help="Server %s poll interval" % "unrescue"),
    # "suspend": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "suspend",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "suspend"),
    cfg.FloatOpt("nova_server_%s_timeout" % "suspend",
                 default=float(300),
                 help="Server %s timeout" % "suspend"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "suspend",
                 default=float(2),
                 help="Server %s poll interval" % "suspend"),
    # "resume": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "resume",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "resume"),
    cfg.FloatOpt("nova_server_%s_timeout" % "resume",
                 default=float(300),
                 help="Server %s timeout" % "resume"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "resume",
                 default=float(2),
                 help="Server %s poll interval" % "resume"),
    # "pause": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "pause",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "pause"),
    cfg.FloatOpt("nova_server_%s_timeout" % "pause",
                 default=float(300),
                 help="Server %s timeout" % "pause"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "pause",
                 default=float(2),
                 help="Server %s poll interval" % "pause"),
    # "unpause": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "unpause",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "unpause"),
    cfg.FloatOpt("nova_server_%s_timeout" % "unpause",
                 default=float(300),
                 help="Server %s timeout" % "unpause"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "unpause",
                 default=float(2),
                 help="Server %s poll interval" % "unpause"),
    # "shelve": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "shelve",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "shelve"),
    cfg.FloatOpt("nova_server_%s_timeout" % "shelve",
                 default=float(300),
                 help="Server %s timeout" % "shelve"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "shelve",
                 default=float(2),
                 help="Server %s poll interval" % "shelve"),
    # "unshelve": (2, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "unshelve",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "unshelve"),
    cfg.FloatOpt("nova_server_%s_timeout" % "unshelve",
                 default=float(300),
                 help="Server %s timeout" % "unshelve"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "unshelve",
                 default=float(2),
                 help="Server %s poll interval" % "unshelve"),
    # "image_create": (0, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "image_create",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "image_create"),
    cfg.FloatOpt("nova_server_%s_timeout" % "image_create",
                 default=float(300),
                 help="Server %s timeout" % "image_create"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "image_create",
                 default=float(2),
                 help="Server %s poll interval" % "image_create"),
    # "image_delete": (0, 300, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "image_delete",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "image_delete"),
    cfg.FloatOpt("nova_server_%s_timeout" % "image_delete",
                 default=float(300),
                 help="Server %s timeout" % "image_delete"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "image_delete",
                 default=float(2),
                 help="Server %s poll interval" % "image_delete"),
    # "resize": (2, 400, 5)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "resize",
                 default=float(2),
                 help="Time to sleep after %s before polling"
                      " for status" % "resize"),
    cfg.FloatOpt("nova_server_%s_timeout" % "resize",
                 default=float(400),
                 help="Server %s timeout" % "resize"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "resize",
                 default=float(5),
                 help="Server %s poll interval" % "resize"),
    # "resize_confirm": (0, 200, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "resize_confirm",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "resize_confirm"),
    cfg.FloatOpt("nova_server_%s_timeout" % "resize_confirm",
                 default=float(200),
                 help="Server %s timeout" % "resize_confirm"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "resize_confirm",
                 default=float(2),
                 help="Server %s poll interval" % "resize_confirm"),
    # "resize_revert": (0, 200, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "resize_revert",
                 default=float(0),
                 help="Time to sleep after %s before polling"
                      " for status" % "resize_revert"),
    cfg.FloatOpt("nova_server_%s_timeout" % "resize_revert",
                 default=float(200),
                 help="Server %s timeout" % "resize_revert"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "resize_revert",
                 default=float(2),
                 help="Server %s poll interval" % "resize_revert"),
    # "live_migrate": (1, 400, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "live_migrate",
                 default=float(1),
                 help="Time to sleep after %s before polling"
                      " for status" % "live_migrate"),
    cfg.FloatOpt("nova_server_%s_timeout" % "live_migrate",
                 default=float(400),
                 help="Server %s timeout" % "live_migrate"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "live_migrate",
                 default=float(2),
                 help="Server %s poll interval" % "live_migrate"),
    # "migrate": (1, 400, 2)
    cfg.FloatOpt("nova_server_%s_prepoll_delay" % "migrate",
                 default=float(1),
                 help="Time to sleep after %s before polling"
                      " for status" % "migrate"),
    cfg.FloatOpt("nova_server_%s_timeout" % "migrate",
                 default=float(400),
                 help="Server %s timeout" % "migrate"),
    cfg.FloatOpt("nova_server_%s_poll_interval" % "migrate",
                 default=float(2),
                 help="Server %s poll interval" % "migrate"),
    # "detach":
    cfg.FloatOpt("nova_detach_volume_timeout",
                 default=float(200),
                 help="Nova volume detach timeout"),
    cfg.FloatOpt("nova_detach_volume_poll_interval",
                 default=float(2),
                 help="Nova volume detach poll interval")
]}
