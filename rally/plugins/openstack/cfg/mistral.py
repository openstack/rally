
from oslo_config import cfg

OPTS = {"benchmark": [
    cfg.IntOpt(
        "mistral_execution_timeout",
        default=200,
        help="mistral execution timeout")
]}
