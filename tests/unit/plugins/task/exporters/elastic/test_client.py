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
from unittest import mock

from rally import exceptions
from rally.plugins.task.exporters.elastic import client
from tests.unit import test


PATH = "rally.plugins.task.exporters.elastic.client"


class ElasticSearchClientTestCase(test.TestCase):
    def test_check_response(self):
        es = client.ElasticSearchClient(None)

        resp = mock.Mock(status_code=200)
        self.assertIsNone(es._check_response(resp))

        resp.status_code = 300
        resp.json.side_effect = ValueError("Foo!!!!")
        resp.text = "something"

        e = self.assertRaises(exceptions.RallyException,
                              es._check_response, resp)
        self.assertEqual("[HTTP 300] Failed to connect to ElasticSearch "
                         "cluster: something", e.format_message())

        resp.json = mock.Mock(return_value={"error": {
            "reason": "I'm too lazy to process this request."}})

        e = self.assertRaises(exceptions.RallyException,
                              es._check_response, resp)
        self.assertEqual("[HTTP 300] Failed to connect to ElasticSearch "
                         "cluster: I'm too lazy to process this request.",
                         e.format_message())

    @mock.patch("%s.ElasticSearchClient.info" % PATH)
    def test_version(self, mock_info):
        es = client.ElasticSearchClient(None)

        es._version = "foo"
        self.assertEqual("foo", es.version())
        self.assertFalse(mock_info.called)

        es._version = None
        self.assertIsNone(es.version())
        mock_info.assert_called_once_with()

    @mock.patch("%s.requests.get" % PATH)
    def test_info(self, mock_requests_get):
        resp = mock_requests_get.return_value
        resp.status_code = 200
        data = {"version": {"number": "5.6.1"}}
        resp.json.return_value = data

        es = client.ElasticSearchClient(None)

        self.assertEqual(data, es.info())

        self.assertEqual("5.6.1", es._version)
        mock_requests_get.assert_called_once_with("http://localhost:9200")

        # check unification
        data = {"version": {"number": "2.4.1",
                            "build_timestamp": "timestamp"}}
        resp.json.return_value = data
        self.assertEqual(
            {"version": {"number": "2.4.1",
                         "build_date": "timestamp"}},
            es.info())

    @mock.patch("%s.ElasticSearchClient._check_response" % PATH)
    @mock.patch("%s.requests.get" % PATH)
    def test_info_fails(self, mock_requests_get, mock__check_response):
        es = client.ElasticSearchClient(None)

        # case #1 - _check_response raises exception. it should not be caught
        exc = KeyError("foo")
        mock__check_response.side_effect = exc

        e = self.assertRaises(KeyError, es.info)
        self.assertEqual(exc, e)

        mock__check_response.reset_mock()
        mock__check_response.side_effect = None

        # case #2 - the response is ok, but the data is not a json-like obj
        resp = mock_requests_get.return_value
        resp.json.side_effect = ValueError()

        es = client.ElasticSearchClient(None)

        e = self.assertRaises(exceptions.RallyException, es.info)
        self.assertIn("The return data doesn't look like a json.",
                      e.format_message())

        resp.json.reset_mock()
        resp.json.side_effect = None
        # case #3 - the return data is a json, but doesn't include the version

        resp.json.return_value = {}
        e = self.assertRaises(exceptions.RallyException, es.info)
        self.assertIn("Failed to parse the received data.",
                      e.format_message())

    @mock.patch("%s.ElasticSearchClient._check_response" % PATH)
    @mock.patch("%s.requests.head" % PATH)
    def test_check_document(self, mock_requests_head, mock__check_response):
        es = client.ElasticSearchClient(None)
        resp = mock_requests_head.return_value

        resp.status_code = 200

        self.assertTrue(es.check_document("foo", "bar"))
        mock_requests_head.assert_called_once_with(
            "http://localhost:9200/foo/data/bar")
        self.assertFalse(mock__check_response.called)

        resp.status_code = 404

        self.assertFalse(es.check_document("foo", "bar"))
        self.assertFalse(mock__check_response.called)

        resp.status_code = 300
        self.assertIsNone(es.check_document("foo", "bar"))
        mock__check_response.assert_called_once_with(resp, mock.ANY)

    @mock.patch("%s.requests.post" % PATH)
    def test_push_documents(self, mock_requests_post):
        mock_requests_post.return_value.status_code = 200
        es = client.ElasticSearchClient(None)
        # decrease the size of chunks to not generate 10_001 number of docs
        es.CHUNK_LENGTH = 2

        documents = ["doc1", "doc2", "doc3"]

        es.push_documents(documents)

        headers = {"Content-Type": "application/x-ndjson"}

        self.assertEqual(
            [mock.call("http://localhost:9200/_bulk",
                       data="doc1\ndoc2\n", headers=headers),
             mock.call("http://localhost:9200/_bulk",
                       data="doc3\n", headers=headers)],
            mock_requests_post.call_args_list
        )

    @mock.patch("%s.ElasticSearchClient._check_response" % PATH)
    @mock.patch("%s.requests.get" % PATH)
    def test_list_indices(self, mock_requests_get, mock__check_response):
        mock_requests_get.return_value.text = "foo bar\n"
        es = client.ElasticSearchClient(None)

        self.assertEqual(["foo", "bar"], es.list_indices())

        mock_requests_get.assert_called_once_with(
            "http://localhost:9200/_cat/indices?v")
        mock__check_response.assert_called_once_with(
            mock_requests_get.return_value, mock.ANY)

    @mock.patch("%s.ElasticSearchClient._check_response" % PATH)
    @mock.patch("%s.requests.put" % PATH)
    def test_create_index_es_5(self, mock_requests_put, mock__check_response):
        es = client.ElasticSearchClient(None)
        es._version = "5"
        i_name = "foo"
        i_type = "data"
        o_properties = {"prop1": {"type": "text"},
                        "prop2": {"type": "keyword"}}
        # ensure that no transformation with properties will not be performed
        properties = copy.deepcopy(o_properties)
        es.create_index(i_name, i_type, properties)

        mock_requests_put.assert_called_once_with(
            "http://localhost:9200/%s" % i_name,
            json={"mappings": {i_type: {"properties": o_properties}}})
        mock__check_response.assert_called_once_with(
            mock_requests_put.return_value, mock.ANY)

    @mock.patch("%s.ElasticSearchClient._check_response" % PATH)
    @mock.patch("%s.requests.put" % PATH)
    def test_create_index_es_2(self, mock_requests_put, mock__check_response):
        es = client.ElasticSearchClient(None)
        es._version = "2.4.3"
        i_name = "foo"
        i_type = "data"
        o_properties = {"prop1": {"type": "text"},
                        "prop2": {"type": "keyword"}}
        # ensure that no transformation with properties will be performed
        properties = copy.deepcopy(o_properties)

        es.create_index(i_name, i_type, properties)

        e_properties = {"prop1": {"type": "string"},
                        "prop2": {"type": "string",
                                  "index": "not_analyzed"}}

        mock_requests_put.assert_called_once_with(
            "http://localhost:9200/%s" % i_name,
            json={"mappings": {i_type: {"properties": e_properties}}})
        mock__check_response.assert_called_once_with(
            mock_requests_put.return_value, mock.ANY)
