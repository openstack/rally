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

import copy

import requests
import six

from rally.common import logging
from rally import exceptions

LOG = logging.getLogger(__name__)


class ElasticSearchClient(object):
    """The helper class for communication with ElasticSearch 2.*, 5.*, 6.*"""

    # a number of documents to push to the cluster at once.
    CHUNK_LENGTH = 10000

    def __init__(self, url):
        self._url = url.rstrip("/") if url else "http://localhost:9200"
        self._version = None

    @staticmethod
    def _check_response(resp, action=None):
        if resp.status_code in (200, 201):
            return
        # it is an error. let's try to find the reason
        reason = None
        try:
            data = resp.json()
        except ValueError:
            # it is ok
            pass
        else:
            if "error" in data:
                if isinstance(data["error"], dict):
                    reason = data["error"].get("reason", "")
                else:
                    reason = data["error"]
        reason = reason or resp.text or "n/a"
        action = action or "connect to"
        raise exceptions.RallyException(
            "[HTTP %s] Failed to %s ElasticSearch cluster: %s" %
            (resp.status_code, action, reason))

    def version(self):
        """Get version of the ElasticSearch cluster."""
        if self._version is None:
            self.info()
        return self._version

    def info(self):
        """Retrieve info about the ElasticSearch cluster."""
        resp = requests.get(self._url)
        self._check_response(resp)
        err_msg = "Failed to retrieve info about the ElasticSearch cluster: %s"
        try:
            data = resp.json()
        except ValueError:
            LOG.debug("Return data from %s: %s" % (self._url, resp.text))
            raise exceptions.RallyException(
                err_msg % "The return data doesn't look like a json.")
        version = data.get("version", {}).get("number")
        if not version:
            LOG.debug("Return data from %s: %s" % (self._url, resp.text))
            raise exceptions.RallyException(
                err_msg % "Failed to parse the received data.")
        self._version = version
        if self._version.startswith("2"):
            data["version"]["build_date"] = data["version"].pop(
                "build_timestamp")
        return data

    def push_documents(self, documents):
        """Push documents to the ElasticSearch cluster using bulk API.

        :param documents: a list of documents to push
        """
        LOG.debug("Pushing %s documents by chunks (up to %s documents at once)"
                  " to ElasticSearch." %
                  # dividing numbers by two, since each documents has 2 lines
                  #     in `documents` (action and document itself).
                  (len(documents) / 2, self.CHUNK_LENGTH / 2))

        for pos in six.moves.range(0, len(documents), self.CHUNK_LENGTH):
            data = "\n".join(documents[pos:pos + self.CHUNK_LENGTH]) + "\n"

            raw_resp = requests.post(
                self._url + "/_bulk", data=data,
                headers={"Content-Type": "application/x-ndjson"}
            )
            self._check_response(raw_resp, action="push documents to")

            LOG.debug("Successfully pushed %s documents." %
                      len(raw_resp.json()["items"]))

    def list_indices(self):
        """List all indices."""
        resp = requests.get(self._url + "/_cat/indices?v")
        self._check_response(resp, "list the indices at")

        return resp.text.rstrip().split(" ")

    def create_index(self, name, doc_type, properties):
        """Create an index.

        There are two very different ways to search strings. You can either
        search whole values, that we often refer to as keyword search, or
        individual tokens, that we usually refer to as full-text search.
        In ElasticSearch 2.x `string` data type is used for these cases whereas
        ElasticSearch 5.0 the `string` data type was replaced by two new types:
        `keyword` and `text`. Since it is hard to predict the destiny of
        `string` data type and support of 2 formats of input data, the
        properties should be transmitted in ElasticSearch 5.x format.
        """
        if self.version().startswith("2."):
            properties = copy.deepcopy(properties)
            for spec in properties.values():
                if spec.get("type", None) == "text":
                    spec["type"] = "string"
                elif spec.get("type", None) == "keyword":
                    spec["type"] = "string"
                    spec["index"] = "not_analyzed"

        resp = requests.put(
            self._url + "/%s" % name,
            json={"mappings": {doc_type: {"properties": properties}}})
        self._check_response(resp, "create index at")

    def check_document(self, index, doc_id, doc_type="data"):
        """Check for the existence of a document.

        :param index: The index of a document
        :param doc_id: The ID of a document
        :param doc_type: The type of a document (Defaults to data)
        """
        resp = requests.head("%(url)s/%(index)s/%(type)s/%(id)s" %
                             {"url": self._url,
                              "index": index,
                              "type": doc_type,
                              "id": doc_id})
        if resp.status_code == 200:
            return True
        elif resp.status_code == 404:
            return False
        else:
            self._check_response(resp, "check the index at")
