
from oslo_config import cfg

OPTS = {"benchmark": [
    cfg.FloatOpt("watcher_audit_launch_poll_interval", default=2.0,
                 help="Watcher audit launch interval"),
    cfg.IntOpt("watcher_audit_launch_timeout", default=300,
               help="Watcher audit launch timeout")
]}
