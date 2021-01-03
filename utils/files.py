import os


def get_meta(meta_file):
    meta = {}
    for line in open(os.path.join(meta_file)).readlines():
        line = line.strip()
        if line:
            line = line.split('=')
            meta[line[0]] = line[1]
    return meta


def get_meta_dict(path):
    res = {}
    for d in os.listdir(path):
        if d.startswith('latest'):
            continue
        d = os.path.join(path, d)
        if len(os.listdir(os.path.join(d, 'dump'))) < 20:
            continue
        if d.split('/')[-1].startswith('baseline'):
            resolution = d.split('_')[-1]
            bitrate = 12000
        else:
            meta_file = os.path.join(d, 'metadata.txt')
            meta = get_meta(meta_file)
            resolution = f"{meta['resolution'].split('x')[0]}p"
            bitrate = meta['bitrate']
        res.setdefault(resolution, {})[bitrate] = d
    return res
