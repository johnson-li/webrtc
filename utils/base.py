import os

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_PATH = os.path.join(PROJECT_PATH, 'resources')
RESULT_PATH = os.path.join(PROJECT_PATH, 'results')
RESULT_DIAGRAM_PATH = os.path.join(RESULT_PATH, 'diagram')
RESULT_IMAGE_PATH = os.path.join(RESULT_PATH, 'image')
RESULT_CACHE_PATH = os.path.join(RESULT_PATH, 'cache')

DATA_PATH = os.path.expanduser('~/Data')
