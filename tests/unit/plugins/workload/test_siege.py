#
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


import sys

from rally.plugins.workload import siege
from tests.unit import test

import mock

SIEGE_OUTPUT = """
Transactions:                    522 hits
Availability:                 100.00 %
Elapsed time:                   3.69 secs
Data transferred:               1.06 MB
Response time:                  0.10 secs
Transaction rate:             141.46 trans/sec
Throughput:                     0.29 MB/sec
Concurrency:                   14.71
Successful transactions:         522
Failed transactions:               0
Longest transaction:            0.26
Shortest transaction:           0.08
"""

OUTPUT = [
    {"output_value": "curl", "descr": "", "output_key": "curl_cli"},
    {"output_value": "wp-net", "descr": "", "output_key": "net_name"},
    {"output_value": ["10.0.0.3", "172.16.0.159"],
     "description": "",
     "output_key": "gate_node"},
    {"output_value": {
        "1": {"wordpress-network": ["10.0.0.4"]},
        "0": {"wordpress-network": ["10.0.0.5"]}},
        "description": "No description given", "output_key": "wp_nodes"}]


class SiegeTestCase(test.TestCase):

    @mock.patch("rally.plugins.workload.siege.json.load")
    def test_get_instances(self, mock_load):
        mock_load.return_value = OUTPUT
        instances = list(siege.get_instances())
        self.assertEqual(["10.0.0.4", "10.0.0.5"], instances)

    @mock.patch("rally.plugins.workload.siege.get_instances")
    @mock.patch("rally.plugins.workload.siege.generate_urls_list")
    @mock.patch("rally.plugins.workload.siege.subprocess.check_output")
    def test_run(self, mock_check_output, mock_generate_urls_list,
                 mock_get_instances):
        mock_get_instances.return_value = [1, 2]
        mock_generate_urls_list.return_value = "urls"
        mock_check_output.return_value = SIEGE_OUTPUT
        mock_write = mock.MagicMock()
        mock_stdout = mock.MagicMock(write=mock_write)
        real_stdout = sys.stdout
        sys.stdout = mock_stdout
        siege.run()
        expected = [mock.call("Transaction rate:141.46\n"),
                    mock.call("Throughput:0.29\n")]
        sys.stdout = real_stdout
        self.assertEqual(expected, mock_write.mock_calls)

    @mock.patch("rally.plugins.workload.siege.tempfile.NamedTemporaryFile")
    def test_generate_urls_list(self, mock_named_temporary_file):
        mock_urls = mock.MagicMock()
        mock_named_temporary_file.return_value = mock_urls
        name = siege.generate_urls_list(["foo", "bar"])
        self.assertEqual(mock_urls.name, name)
