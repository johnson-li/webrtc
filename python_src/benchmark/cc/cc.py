class CongestionControl(object):
    def __init__(self):
        pass

    def on_ack(self, pkg_id):
        raise NotImplementedError()

    def next(self, pkg_id) -> bool:
        raise NotImplementedError()

    def on_sent(self, pkg_id, sent: bool):
        raise NotImplementedError()
