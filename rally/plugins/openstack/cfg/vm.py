
from oslo_config import cfg

OPTS = {"benchmark": [
    cfg.FloatOpt("vm_ping_poll_interval", default=1.0,
                 help="Interval between checks when waiting for a VM to "
                 "become pingable"),
    cfg.FloatOpt("vm_ping_timeout", default=120.0,
                 help="Time to wait for a VM to become pingable")
]}
