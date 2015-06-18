# Copyright 2015 Mirantis Inc.
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

import time

from oslo_config import cfg

from rally.benchmark.scenarios import base
from rally.benchmark import utils as bench_utils


MANILA_BENCHMARK_OPTS = [
    cfg.FloatOpt(
        "manila_share_create_prepoll_delay",
        default=2.0,
        help="Delay between creating Manila share and polling for its "
             "status."),
    cfg.FloatOpt(
        "manila_share_create_timeout",
        default=300.0,
        help="Timeout for Manila share creation."),
    cfg.FloatOpt(
        "manila_share_create_poll_interval",
        default=3.0,
        help="Interval between checks when waiting for Manila share "
             "creation."),
    cfg.FloatOpt(
        "manila_share_delete_timeout",
        default=180.0,
        help="Timeout for Manila share deletion."),
    cfg.FloatOpt(
        "manila_share_delete_poll_interval",
        default=2.0,
        help="Interval between checks when waiting for Manila share "
             "deletion."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MANILA_BENCHMARK_OPTS, group=benchmark_group)


class ManilaScenario(base.Scenario):
    """Base class for Manila scenarios with basic atomic actions."""

    @base.atomic_action_timer("manila.create_share")
    def _create_share(self, share_proto, size=1, **kwargs):
        """Create a share.

        :param share_proto: share protocol for new share,
            available values are NFS, CIFS, GlusterFS and HDFS.
        :param size: size of a share in GB
        :param snapshot_id: ID of the snapshot
        :param name: name of new share
        :param description: description of a share
        :param metadata: optional metadata to set on share creation
        :param share_network: either instance of ShareNetwork or str with ID
        :param share_type: either instance of ShareType or str with ID
        :param is_public: defines whether to set share as public or not.
        :returns: instance of :class:`Share`
        """
        if not kwargs.get("name"):
            kwargs["name"] = self._generate_random_name()

        share = self.clients("manila").shares.create(
            share_proto, size, **kwargs)
        time.sleep(CONF.benchmark.manila_share_create_prepoll_delay)
        share = bench_utils.wait_for(
            share,
            is_ready=bench_utils.resource_is("available"),
            update_resource=bench_utils.get_from_manager(),
            timeout=CONF.benchmark.manila_share_create_timeout,
            check_interval=CONF.benchmark.manila_share_create_poll_interval,
        )
        return share

    @base.atomic_action_timer("manila.delete_share")
    def _delete_share(self, share):
        """Delete the given share.

        :param share: :class:`Share`
        """
        share.delete()
        error_statuses = ("error_deleting", )
        bench_utils.wait_for_delete(
            share,
            update_resource=bench_utils.get_from_manager(error_statuses),
            timeout=CONF.benchmark.manila_share_delete_timeout,
            check_interval=CONF.benchmark.manila_share_delete_poll_interval)

    @base.atomic_action_timer("manila.list_shares")
    def _list_shares(self, detailed=True, search_opts=None):
        """Returns user shares list.

        :param detailed: defines either to return detailed list of
            objects or not.
        :param search_opts: container of search opts such as
            "name", "host", "share_type", etc.
        """
        return self.clients("manila").shares.list(
            detailed=detailed, search_opts=search_opts)
