import json
import os
import sys

import gevent.monkey

BACKEND_BASE_PATH = os.path.dirname(os.path.abspath(__file__))
BACKEND_CONFIG_PATH = os.path.join(BACKEND_BASE_PATH, '../backend.config.json')
BACKEND_VAR_DIR_PATH = os.path.join(BACKEND_BASE_PATH, 'var')
SIM_DATA_PATH = os.path.join(BACKEND_BASE_PATH, '../simData')
SIM_CONFIG_PATH = os.path.join(BACKEND_VAR_DIR_PATH, 'config.json')
START_URL = '/index.html'

# DON'T CHANGE THIS PORT NUMBER, which is referred when you run "$ npm
# run serve"
LISTEN_PORT_FOR_DEVELOPMENT = 8081
WEB_ROOT_PATH_FOR_DEVELOPMENT = os.path.join(BACKEND_BASE_PATH, '../public')

LISTEN_PORT_FOR_PRODUCTION = 8080
WEB_ROOT_PATH_FOR_PRODUCTION = os.path.join(BACKEND_BASE_PATH, '../dist')

web_root_path = None


def init_web_root_path(dev_mode=False):
    global web_root_path
    if dev_mode:
        web_root_path = WEB_ROOT_PATH_FOR_DEVELOPMENT
    else:
        web_root_path = WEB_ROOT_PATH_FOR_PRODUCTION
        if os.path.exists(web_root_path) is False:
            sys.stderr.write(
                '"dist" is not available; did you run "npm run build"?\n'
            )
            sys.stderr.write('backend server is shutting down...\n')
            sys.exit(1)


def get_web_root_path():
    global web_root_path
    return web_root_path

def get_simulator_path():
    with open(BACKEND_CONFIG_PATH) as f:
        config = json.load(f)
        simulator_path = config['simulator_path']

    if simulator_path is None:
        return None
    elif os.path.isabs(simulator_path):
        return simulator_path
    else:
        # simulator_path is a relative path
        return os.path.join(
            os.path.dirname(BACKEND_CONFIG_PATH),
            simulator_path
        )


def get_trace_dir_path():
    with open(BACKEND_CONFIG_PATH) as f:
        config = json.load(f)
        trace_dir_path = config['trace_dir_path']

    if trace_dir_path is None:
        raise ValueError('trace_dir_path is not found')
    else:
        return os.path.join(
            os.path.dirname(BACKEND_CONFIG_PATH),
            trace_dir_path
        )

# add the path of the simulator source directory to Python module
# search path list so that SimEngine and other relevant modules can be
# imported
sys.path.insert(0, get_simulator_path())

# do monkey patching here before eel is imported
# https://github.com/ChrisKnott/Eel#asynchronous-python
gevent.monkey.patch_all()
