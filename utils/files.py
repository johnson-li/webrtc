import os


def get_meta(meta_file):
    meta = {}
    for line in open(os.path.join(meta_file)).readlines():
        line = line.strip()
        if line:
            line = line.split('=')
            meta[line[0]] = line[1]
    return meta
