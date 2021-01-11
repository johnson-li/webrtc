RESOLUTION = (1920, 1280)
RESOLUTIONS = ((1920, 1280), (1680, 1120), (1440, 960), (1200, 800), (960, 640), (720, 480), (480, 320))


def get_resolution(name):
    for res in RESOLUTIONS:
        if name == f'{res[1]}p':
            return res


def get_resolution_p(name):
    return to_resolution(name.split('x'))


def to_resolution(resolution):
    for r in RESOLUTIONS:
        if str(r[0]) == str(resolution[0]):
            return f'{r[1]}p'
    return f'{resolution[1]}p'
