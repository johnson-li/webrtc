import os

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
PROJECT_PATH = os.path.dirname(DIR_PATH)
DATA_PATH = os.path.join(PROJECT_PATH, 'data')
SCRIPTS_PATH = os.path.join(PROJECT_PATH, 'scripts')
RESULTS_PATH = os.path.join(PROJECT_PATH, 'results')
REMOTE_PATH = '/tmp/webrtc'
REMOTE_LOG_PATH = os.path.join(REMOTE_PATH, 'logs')

