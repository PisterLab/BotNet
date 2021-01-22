from __future__ import print_function
import json
import os
import subprocess
import sys

# import backend.routes before eel so that our custom routes are
# processed first. this is needed to provide a GET route to
# '/results/*.zip'. otherwise route to <path:path> in Eel will
# prevents that.
import backend.routes
import eel

import backend
# need to import backend.sim to expose its APIs
import backend.sim

CONFIG_JSON_TEMPLATE = {
    'version': 0,
    'execution': {
        'numCPUs': 1,
        'numRuns': 1,
    },
    'settings': {},
    'logging': 'all',
    'log_directory_name': 'startTime',
    'post': []
}


def on_close_callback(page, sockets):
    print('Detect a WebSocket is closed; keep running')
    backend.sim.clear_sim()


def start_server(dev_mode=False):
    # prepare 'var' directory
    if os.path.exists(backend.BACKEND_VAR_DIR_PATH) is False:
        os.mkdir(backend.BACKEND_VAR_DIR_PATH)

    # initialize eel
    backend.init_web_root_path(dev_mode)
    web_root = backend.get_web_root_path()
    eel.init(web_root)

    try:
        create_config_json()
        _start(dev_mode)
    finally:
        _delete_config_json()
        _delete_tmp_files()


def _start(dev_mode):
    # start the server

    with open(backend.BACKEND_CONFIG_PATH) as f:
        config = json.load(f)

    if dev_mode:
        listen_port = backend.LISTEN_PORT_FOR_DEVELOPMENT
    else:
        listen_port = backend.LISTEN_PORT_FOR_PRODUCTION
    print('Starting the backend server on {0}:{1}'.format(
        config['host'],
        listen_port
    ))
    sys.stdout.flush()
    eel.start(
        backend.START_URL,
        host     = config['host'],
        port     = listen_port,
        mode     = None,
        callback = on_close_callback
    )



def create_config_json():
    # read the default config.json from the simulator source directory
    default_config_path = os.path.join(
        backend.get_simulator_path(),
        'bin/config.json'
    )
    with open(default_config_path) as f:
        default_config = json.load(f)

    # check its settings
    check_config_json = os.path.join(
        backend.get_simulator_path(),
        'bin/check_config_json.py'
    )
    popen = subprocess.Popen(
        [sys.executable, check_config_json, '-s', '-c', '-'],
        stdin  = subprocess.PIPE,
        stdout = subprocess.PIPE
    )
    _ = popen.communicate(json.dumps(default_config))
    if popen.returncode != 0:
        raise ValueError('invalid default config.json')

    # create a new config.json
    config = dict(CONFIG_JSON_TEMPLATE)
    config['settings'] = default_config['settings']

    config_dir = os.path.dirname(backend.SIM_CONFIG_PATH)
    if os.path.exists(config_dir) is True:
        _delete_config_json()
    else:
        os.mkdir(config_dir)

    with open(backend.SIM_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)


def _delete_config_json():
    if os.path.exists(backend.SIM_CONFIG_PATH):
        print('removing {0}'.format(backend.SIM_CONFIG_PATH))
        os.remove(backend.SIM_CONFIG_PATH)


def _delete_tmp_files():
    for root, _, files in os.walk(backend.BACKEND_VAR_DIR_PATH):
        for file_name in files:
            if file_name.startswith('tmp'):
                tmp_file_path = os.path.join(root, file_name)
                print('removing {0}'.format(tmp_file_path))
                os.remove(tmp_file_path)
