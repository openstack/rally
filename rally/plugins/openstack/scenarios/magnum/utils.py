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

from rally.common import utils as common_utils
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

MAGNUM_BENCHMARK_OPTS = [
    cfg.FloatOpt("magnum_bay_create_prepoll_delay",
                 default=5.0,
                 help="Time(in sec) to sleep after creating a resource before "
                      "polling for the status."),
    cfg.FloatOpt("magnum_bay_create_timeout",
                 default=1200.0,
                 help="Time(in sec) to wait for magnum bay to be created."),
    cfg.FloatOpt("magnum_bay_create_poll_interval",
                 default=1.0,
                 help="Time interval(in sec) between checks when waiting for "
                      "bay creation."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MAGNUM_BENCHMARK_OPTS, group=benchmark_group)


class MagnumScenario(scenario.OpenStackScenario):
    """Base class for Magnum scenarios with basic atomic actions."""

    @atomic.action_timer("magnum.list_baymodels")
    def _list_baymodels(self, **kwargs):
        """Return list of baymodels.

        :param limit: (Optional) The maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of baymodels to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for baymodels listing

        :returns: baymodels list
        """

        return self.clients("magnum").baymodels.list(**kwargs)

    @atomic.action_timer("magnum.create_baymodel")
    def _create_baymodel(self, **kwargs):
        """Create a baymodel

        :param kwargs: optional additional arguments for baymodel creation
        :returns: magnum baymodel
        """

        kwargs["name"] = self.generate_random_name()

        return self.clients("magnum").baymodels.create(**kwargs)

    @atomic.action_timer("magnum.list_bays")
    def _list_bays(self, limit=None, **kwargs):
        """Return list of bays.

        :param limit: (Optional) the maximum number of results to return
                      per request, if:

            1) limit > 0, the maximum number of bays to return.
            2) limit param is NOT specified (None), the number of items
               returned respect the maximum imposed by the Magnum API
               (see Magnum's api.max_limit option).
        :param kwargs: Optional additional arguments for bays listing

        :returns: bays list
        """
        return self.clients("magnum").bays.list(limit=limit, **kwargs)

    @atomic.action_timer("magnum.create_bay")
    def _create_bay(self, baymodel, node_count, **kwargs):
        """Create a bay

        :param baymodel: baymodel for the bay
        :param node_count: the bay node count
        :param kwargs: optional additional arguments for bay creation
        :returns: magnum bay
        """

        name = self.generate_random_name()
        bay = self.clients("magnum").bays.create(
            name=name, baymodel_id=baymodel,
            node_count=node_count, **kwargs)

        common_utils.interruptable_sleep(
            CONF.benchmark.magnum_bay_create_prepoll_delay)
        bay = utils.wait_for_status(
            bay,
            ready_statuses=["CREATE_COMPLETE"],
            update_resource=utils.get_from_manager(),
            timeout=CONF.benchmark.magnum_bay_create_timeout,
            check_interval=CONF.benchmark.magnum_bay_create_poll_interval,
            id_attr="uuid"
        )
        return bay
