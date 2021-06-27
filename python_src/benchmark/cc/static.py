from benchmark.reliable_utils import timestamp
from benchmark.cc.cc import CongestionControl


class StaticPacing(CongestionControl):
    def __init__(self, interval):
        self.start_ts = timestamp()
        self.interval = interval
        CongestionControl.__init__(self)

    def on_ack(self, pkg_id):
        pass

    def next(self, pkg_id) -> bool:
        return (timestamp() - self.start_ts) >= (pkg_id * self.interval / 1000)

    def on_sent(self, pkg_id, sent: bool):
        pass
