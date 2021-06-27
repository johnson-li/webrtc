from benchmark.cc.cc import CongestionControl


class BBR(CongestionControl):
    def on_ack(self, pkg_id):
        pass

    def on_sent(self, pkg_id):
        pass

    def next(self, pkg_id) -> bool:
        pass
