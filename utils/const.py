RESOLUTION = (1920, 1280)
RESOLUTIONS = ((1920, 1280), (1680, 1120), (1440, 960), (1200, 800), (960, 640), (720, 480), (480, 320))


def get_resolution(name):
    for res in RESOLUTIONS:
        if name == f'{res[0]}p':
            return res
