from rally.common import logging


LOG = logging.getLogger(__name__)
LOG.warning("rally.osclients module moved to rally.plugins.openstack.osclients"
            "rally.osclients module is going to be removed.")


from rally.plugins.openstack.osclients import *   # noqa
