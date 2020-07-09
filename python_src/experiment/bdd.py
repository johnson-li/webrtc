import json
import os
from experiment.dataset import DataSet

DATA_PATH = os.path.expanduser('~/Data/bdd/bdd100k')
VIDEO_PATH = os.path.join(DATA_PATH, 'videos/val')
LABEL_PATH = os.path.join(DATA_PATH, 'labels/bdd100k_labels_images_val.json')


class BddDataSet(DataSet):
    def __init__(self):
        super(BddDataSet, self).__init__('Berkeley DeepDrive')

    def cache_images(self):
        pass

    def images(self):
        pass


def main():
    labels = json.load(open(LABEL_PATH, 'r'))
    print(labels[0]['name'])
    print(labels[0]['labels'][0])


if __name__ == '__main__':
    main()
