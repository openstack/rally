
from rally.benchmark.context import base
from rally import log as logging
from rally import osclients
from rally import utils

LOG = logging.getLogger(__name__)


@base.context(name="create_flavor", order=1000)
class CreateFlavorContext(base.Context):
    """This sample create flavor with specified options before task starts and
    delete it after task completion.

    To create your own context plugin, inherit it from
    rally.benchmark.context.base.Context
    """

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": utils.JSON_SCHEMA,
        "additionalProperties": False,
        "properties": {
            "flavor_name": {
                "type": "string",
            },
            "ram": {
                "type": "integer",
                "minimum": 1
            },
            "vcpus": {
                "type": "integer",
                "minimum": 1
            },
            "disk": {
                "type": "integer",
                "minimum": 1
            }
        }
    }

    def setup(self):
        """This method is called before task start"""
        try:
            # use rally.osclients to get nessesary client instance
            nova = osclients.Clients(self.context["admin"]["endpoint"]).nova()
            # and than do what you need with this client
            self.context["flavor"] = nova.flavors.create(
                # context settings are stored in self.config
                name=self.config.get("flavor_name", "rally_test_flavor"),
                ram=self.config.get("ram", 1),
                vcpus=self.config.get("vcpus", 1),
                disk=self.config.get("disk", 1)).to_dict()
            LOG.debug("Flavor with id '%s'" % self.context["flavor"]["id"])
        except Exception as e:
            msg = "Can't create flavor: %s" % e.message
            if logging.is_debug():
                LOG.exception(msg)
            else:
                LOG.warning(msg)

    def cleanup(self):
        """This method is called after task finish"""
        try:
            nova = osclients.Clients(self.context["admin"]["endpoint"]).nova()
            nova.flavors.delete(self.context["flavor"]["id"])
            LOG.debug("Flavor '%s' deleted" % self.context["flavor"]["id"])
        except Exception as e:
            msg = "Can't delete flavor: %s" % e.message
            if logging.is_debug():
                LOG.exception(msg)
            else:
                LOG.warning(msg)
