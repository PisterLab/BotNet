#!/usr/bin/env python

# CONSTANTS
from __future__ import print_function
import json
import os
import signal

# we CANNOT import backend and refer its variables because importing
# backend causes gevent to get imported that prevents watchdog from
# working correctly.
BACKEND_ROOTDIR_PATH = os.path.dirname(__file__)
BACKEND_CONFIG_PATH_PATH = os.path.join(
    BACKEND_ROOTDIR_PATH,
    '../backend.config.json'
)
with open(BACKEND_CONFIG_PATH_PATH, 'r') as f:
    config = json.load(f)
SIM_ENGINE_MODULE_PATH = os.path.join(
    config['simulator_path'],
    'SimEngine'
)

# add the parent directory of this file to Python module search path
# so that backend.utils can be imported
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# command line options
import argparse
parser = argparse.ArgumentParser()
parser.add_argument(
    '--dev',
    action  = 'store_true',
    default = False,
    help    = 'start for development',
    dest    = 'dev_mode'
)
parser.add_argument(
    '--auto-restart',
    action  = 'store_true',
    default = False,
    help    = 'restart server on any change of .py file',
    dest    = 'auto_restart'
)
args = parser.parse_args()

# make sure auto_restart is False when this command is executed
# without any command-line option in order to prevent a infinite loop
# of calling this script (fool proof)
assert sys.argv[0] == __file__
if len(sys.argv) == 1:
    # this means there is no command-line option
    assert args.auto_restart is False

# functions to start/stop sever
sever_process = None

def start_server(dev_mode):
    global server_process
    if dev_mode:
        args = ['--dev']
    else:
        args = []
    server_process = subprocess.Popen([sys.executable, __file__] + args)

def stop_server():
    global server_process
    server_process.send_signal(signal.SIGINT)

# main body of this script
import subprocess
if args.auto_restart is True:
    # start the server in a separate process
    start_server(args.dev_mode)

    # watch file system events under BACKEND_ROOTDIR_PATH and
    # SIM_ENGINE_MODULE_PATH and restart the server on any event
    import json
    import time
    import watchdog.observers
    import watchdog.events

    class PythonFileEventHandler(watchdog.events.PatternMatchingEventHandler):
        def __init__(self):
            super(PythonFileEventHandler, self).__init__(patterns=['*.py'])

        def on_any_event(self, event):
            print('restarting server...')
            stop_server()
            start_server(args.dev_mode)

    # setup watchdog observer
    event_handler = PythonFileEventHandler()
    observer = watchdog.observers.Observer()
    print('Start watching .py files under "{0}"'.format(BACKEND_ROOTDIR_PATH))
    observer.schedule(event_handler, BACKEND_ROOTDIR_PATH, recursive=True)
    print('Start watching .py files under "{0}"'.format(SIM_ENGINE_MODULE_PATH))
    observer.schedule(event_handler, SIM_ENGINE_MODULE_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
        assert False # shouldn't come here
    except BaseException:
        # catch all types of exception
        sys.stderr.write('terminating...\n')
    finally:
        # stop backend server (process)
        stop_server()

    try:
        observer.stop()
    except KeyboardInterrupt:
        # for some reason, observer.stop() raises a Keyboardinterrupt
        # exception (happened on macOS) when this script is invoked
        # through "npm run" and killed by Ctrl-C. it seems npm sends
        # the INT signal twice to a process running this process. but
        # not sure exactly what happened. this try...except... block
        # handles that situation so that npm ends without error.
        sys.stderr.write('KeyboardInterrupt is raised again...\n')
        import traceback
        traceback.print_exc()

    observer.join()

else:
    # start the backend server DON'T import 'backend' and its
    # submodules before importing 'watchdog' because 'watchdog'
    # doesn't work with 'gevent' that is imported by 'backend'
    import backend.utils
    backend.utils.start_server(args.dev_mode)
