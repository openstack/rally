import random

from rally.benchmark.runners import base
from rally.common import utils


class RandomTimesScenarioRunner(base.ScenarioRunner):
    """Sample of scenario runner plugin.

    Run scenario random number of times, which is choosen between min_times and
    max_times.
    """

    __execution_type__ = "random_times"

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": utils.JSON_SCHEMA,
        "properties": {
            "type": {
                "type": "string"
            },
            "min_times": {
                "type": "integer",
                "minimum": 1
            },
            "max_times": {
                "type": "integer",
                "minimum": 1
            }
        },
        "additionalProperties": True
    }

    def _run_scenario(self, cls, method_name, context, args):
        # runners settings are stored in self.config
        min_times = self.config.get('min_times', 1)
        max_times = self.config.get('max_times', 1)

        for i in range(random.randrange(min_times, max_times)):
            run_args = (i, cls, method_name,
                        base._get_scenario_context(context), args)
            result = base._run_scenario_once(run_args)
            # use self.send_result for result of each iteration
            self._send_result(result)
