
# we want the following for both actions and workloads
common_dimensions = {
    "args_hash": {"path_in_report": "workload.args_hash"},
    "runner_hash": {"path_in_report": "workload.runner_hash"},
    "contexts_hash": {"path_in_report": "workload.contexts_hash"},
    "subtask_uuid": {"path_in_report": "workload.subtask_uuid"},
}

dimensions = {
    'rally': {
        "tags": {"path_in_report": "task.tags"}
    },
    'rally.workload': common_dimensions,
    'rally.action': common_dimensions,
#    "rally.action.glance_v2": {
#        "test": {"path_in_report": "@", "debug": "rally.action.glance_v2.get_image.duration"}
#    }
}

metrics = {
    'action': [
#        {'name': 'duration', 'path_in_report': "action", "debug": "rally.action.glance_v2.get_image.duration" },
        {
            'name': 'duration',
            'path_in_report': "action.duration"
        },
        {
            'name': 'success',
            'path_in_report': "action.success",
            "transform": float
        }
    ],
    'workload': [
        {
            'name': 'load_duration',
            'path_in_report': "workload.load_duration"
        },
        {
            'name': 'success_rate',
            'path_in_report': "workload.success_rate"
        },
        {
            'name': 'pass_sla',
            'path_in_report': 'workload.pass_sla',
            "transform": float
        }
    ],
    'task': [
        {
            'name': 'pass_sla',
            'path_in_report': 'task.pass_sla',
            "transform": float,
        }
    ]
}
