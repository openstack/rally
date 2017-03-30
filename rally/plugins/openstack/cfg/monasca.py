
from oslo_config import cfg

OPTS = {"benchmark": [
    cfg.FloatOpt(
        "monasca_metric_create_prepoll_delay",
        default=15.0,
        help="Delay between creating Monasca metrics and polling for "
             "its elements.")
]}
