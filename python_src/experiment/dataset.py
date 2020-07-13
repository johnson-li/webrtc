import time
import matplotlib.pyplot as plt


class DataSet:
    def __init__(self, name=None):
        self.name_ = name

    def cache_images(self):
        raise NotImplementedError()

    def images(self):
        raise NotImplementedError()

    def illustrate(self):
        figure = plt.figure(figsize=(9, 6), dpi=100)
        ax = figure.gca()
        im = None
        index = 0
        start_ts1 = time.time()
        start_ts2 = 0
        for img, timestamp in self.images():
            if not im:
                im = ax.imshow(img)
            else:
                im.set_data(img)
            plt.draw()
            if not start_ts2:
                start_ts2 = timestamp
            wait = max(.001, (timestamp - start_ts2) / 1000000.0 - (time.time() - start_ts1))
            plt.pause(.001)
            time.sleep(wait - .001)
            index += 1
            if index > 100:
                break
