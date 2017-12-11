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

import json
import os
from rally.common import logging
from rally.common.plugin import plugin
from rally.task.processing.charts import OutputTextArea

LOG = logging.getLogger(__name__)


def _datetime_json_serialize(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    else:
        return obj


@plugin.configure(name="OSProfiler")
class OSProfilerChart(OutputTextArea):
    """osprofiler content

    This plugin complete data of osprofiler

    """

    widget = "OSProfiler"

    @classmethod
    def get_osprofiler_data(cls, data):

        from osprofiler import cmd
        from osprofiler.drivers import base

        try:
            engine = base.get_driver(data["data"]["conn_str"])
        except Exception:
            if logging.is_debug():
                LOG.exception("Error while fetching OSProfiler results.")
            return None

        data["widget"] = "EmbedChart"
        data["title"] = "{0} : {1}".format(data["title"],
                                           data["data"]["trace_id"][0])

        path = "%s/template.html" % os.path.dirname(cmd.__file__)
        with open(path) as f:
            html_obj = f.read()

        osp_data = engine.get_report(data["data"]["trace_id"][0])
        osp_data = json.dumps(osp_data,
                              indent=4,
                              separators=(",", ": "),
                              default=_datetime_json_serialize)
        data["data"] = html_obj.replace("$DATA", osp_data)
        data["data"] = data["data"].replace("$LOCAL", "false")

        # NOTE(chenxu): self._data will be passed to
        # ["complete_output"]["data"] as a whole string and
        # tag </script> will be parsed incorrectly in javascript string
        # so we turn it to <\/script> and turn it back in javascript.
        data["data"] = data["data"].replace("/script>", "\/script>")

        return {"title": data["title"],
                "widget": data["widget"],
                "data": data["data"]}

    @classmethod
    def render_complete_data(cls, data):
        if data["data"].get("conn_str"):
            result = cls.get_osprofiler_data(data)
            if result:
                return result
        return {"title": data["title"],
                "widget": "TextArea",
                "data": data["data"]["trace_id"]}
