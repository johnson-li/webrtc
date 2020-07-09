class DataSet:
    def __init__(self, name=None):
        self.name_ = name

    def cache_images(self):
        raise NotImplementedError()

    def images(self):
        raise NotImplementedError()
