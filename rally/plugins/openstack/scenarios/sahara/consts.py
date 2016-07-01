# Copyright 2015: Mirantis Inc.
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

NODE_PROCESSES = {
    "vanilla": {
        "1.2.1": {
            "master": ["namenode", "jobtracker", "oozie"],
            "worker": ["datanode", "tasktracker"]
        },
        "2.3.0": {
            "master": ["namenode", "resourcemanager", "historyserver",
                       "oozie"],
            "worker": ["datanode", "nodemanager"]
        },
        "2.4.1": {
            "master": ["namenode", "resourcemanager", "historyserver",
                       "oozie"],
            "worker": ["datanode", "nodemanager"]
        },
        "2.6.0": {
            "master": ["namenode", "resourcemanager", "historyserver",
                       "oozie"],
            "worker": ["datanode", "nodemanager"]
        },
        "2.7.1": {
            "master": ["namenode", "resourcemanager", "historyserver",
                       "oozie"],
            "worker": ["datanode", "nodemanager"]
        }
    },
    "hdp": {
        "1.3.2": {
            "master": ["JOBTRACKER", "NAMENODE", "SECONDARY_NAMENODE",
                       "GANGLIA_SERVER", "NAGIOS_SERVER",
                       "AMBARI_SERVER", "OOZIE_SERVER"],
            "worker": ["TASKTRACKER", "DATANODE", "HDFS_CLIENT",
                       "MAPREDUCE_CLIENT", "OOZIE_CLIENT", "PIG"]
        },
        "2.0.6": {
            "manager": ["AMBARI_SERVER", "GANGLIA_SERVER",
                        "NAGIOS_SERVER"],
            "master": ["NAMENODE", "SECONDARY_NAMENODE",
                       "ZOOKEEPER_SERVER", "ZOOKEEPER_CLIENT",
                       "HISTORYSERVER", "RESOURCEMANAGER",
                       "OOZIE_SERVER"],
            "worker": ["DATANODE", "HDFS_CLIENT", "ZOOKEEPER_CLIENT",
                       "PIG", "MAPREDUCE2_CLIENT", "YARN_CLIENT",
                       "NODEMANAGER", "OOZIE_CLIENT"]
        },
        "2.2": {
            "manager": ["AMBARI_SERVER", "GANGLIA_SERVER",
                        "NAGIOS_SERVER"],
            "master": ["NAMENODE", "SECONDARY_NAMENODE",
                       "ZOOKEEPER_SERVER", "ZOOKEEPER_CLIENT",
                       "HISTORYSERVER", "RESOURCEMANAGER",
                       "OOZIE_SERVER"],
            "worker": ["DATANODE", "HDFS_CLIENT", "ZOOKEEPER_CLIENT",
                       "PIG", "MAPREDUCE2_CLIENT", "YARN_CLIENT",
                       "NODEMANAGER", "OOZIE_CLIENT", "TEZ_CLIENT"]
        }
    },
    "cdh": {
        "5": {
            "manager": ["CLOUDERA_MANAGER"],
            "master": ["HDFS_NAMENODE", "YARN_RESOURCEMANAGER",
                       "OOZIE_SERVER", "YARN_JOBHISTORY",
                       "HDFS_SECONDARYNAMENODE", "HIVE_METASTORE",
                       "HIVE_SERVER2"],
            "worker": ["YARN_NODEMANAGER", "HDFS_DATANODE"]
        },
        "5.4.0": {
            "manager": ["CLOUDERA_MANAGER"],
            "master": ["HDFS_NAMENODE", "YARN_RESOURCEMANAGER",
                       "OOZIE_SERVER", "YARN_JOBHISTORY",
                       "HDFS_SECONDARYNAMENODE", "HIVE_METASTORE",
                       "HIVE_SERVER2"],
            "worker": ["YARN_NODEMANAGER", "HDFS_DATANODE"]
        },
        "5.5.0": {
            "manager": ["CLOUDERA_MANAGER"],
            "master": ["HDFS_NAMENODE", "YARN_RESOURCEMANAGER",
                       "OOZIE_SERVER", "YARN_JOBHISTORY",
                       "HDFS_SECONDARYNAMENODE", "HIVE_METASTORE",
                       "HIVE_SERVER2"],
            "worker": ["YARN_NODEMANAGER", "HDFS_DATANODE"]
        }
    },
    "spark": {
        "1.3.1": {
            "master": ["namenode", "master"],
            "worker": ["datanode", "slave"]
        },
        "1.6.0": {
            "master": ["namenode", "master"],
            "worker": ["datanode", "slave"]
        }
    },
    "ambari": {
        "2.3": {
            "master-edp": ["Hive Metastore", "HiveServer", "Oozie"],
            "master": ["Ambari", "MapReduce History Server",
                       "Spark History Server", "NameNode", "ResourceManager",
                       "SecondaryNameNode", "YARN Timeline Server",
                       "ZooKeeper"],
            "worker": ["DataNode", "NodeManager"]
        }
    },
    "mapr": {
        "5.0.0.mrv2": {
            "master": ["Metrics", "Webserver", "Zookeeper", "HTTPFS",
                       "Oozie", "FileServer", "CLDB", "Flume", "Hue",
                       "NodeManager", "HistoryServer", "ResourseManager",
                       "HiveServer2", "HiveMetastore", "Sqoop2-Client",
                       "Sqoop2-Server"],
            "worker": ["NodeManager", "FileServer"]
        },
        "5.1.0.mrv2": {
            "master": ["Metrics", "Webserver", "Zookeeper", "HTTPFS",
                       "Oozie", "FileServer", "CLDB", "Flume", "Hue",
                       "NodeManager", "HistoryServer", "ResourseManager",
                       "HiveServer2", "HiveMetastore", "Sqoop2-Client",
                       "Sqoop2-Server"],
            "worker": ["NodeManager", "FileServer"]
        }
    }
}

REPLICATION_CONFIGS = {
    "vanilla": {
        "1.2.1": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.3.0": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.4.1": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.6.0": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.7.1": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        }
    },
    "hdp": {
        "1.3.2": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.0.6": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "2.2": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        }
    },
    "cdh": {
        "5": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        },
        "5.4.0": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        },
        "5.5.0": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        }
    },
    "spark": {
        "1.3.1": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        },
        "1.6.0": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        }
    },
    "ambari": {
        "2.3": {
            "target": "HDFS",
            "config_name": "dfs_replication"
        }
    },
    "mapr": {
        "5.0.0.mrv2": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        },
        "5.1.0.mrv2": {
            "target": "HDFS",
            "config_name": "dfs.replication"
        }
    }

}

ANTI_AFFINITY_PROCESSES = {
    "vanilla": {
        "1.2.1": ["datanode"],
        "2.3.0": ["datanode"],
        "2.4.1": ["datanode"],
        "2.6.0": ["datanode"],
        "2.7.1": ["datanode"]
    },
    "hdp": {
        "1.3.2": ["DATANODE"],
        "2.0.6": ["DATANODE"],
        "2.2": ["DATANODE"]
    },
    "cdh": {
        "5": ["HDFS_DATANODE"],
        "5.4.0": ["HDFS_DATANODE"],
        "5.5.0": ["HDFS_DATANODE"]
    },
    "spark": {
        "1.3.1": ["datanode"],
        "1.6.0": ["datanode"]
    },
    "ambari": {
        "2.3": ["DataNode"],
    },
    "mapr": {
        "5.0.0.mrv2": ["FileServer"],
        "5.1.0.mrv2": ["FileServer"],
    }
}
