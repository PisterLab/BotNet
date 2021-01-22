#!/usr/bin/env python

from __future__ import print_function
import argparse
import inspect
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from SimEngine import SimSettings

CONFIG_VERSION = 0
CONFIG_KEYS_FOR_RUNSIM = ['execution', 'post']
CONFIG_KEYS_FOR_SIMLOG = ['logging', 'log_directory_name']

parser = argparse.ArgumentParser(
    description     = 'config.json checker',
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument(
    '-c', '--config',
    help    = 'the path to your config.json file to check',
    type    = str,
    dest    = 'config_json',
    default = os.path.join(os.path.dirname(__file__), 'config.json')
)
parser.add_argument(
    '-k', '--keys',
    help    = 'dump valid setting keys',
    action  = 'store_true',
    dest    = 'dump_keys',
    default = False
)
parser.add_argument(
    '-s', '--only-settings',
    help    = 'check only \"settings\" part',
    action  = 'store_true',
    dest    = 'only_settings',
    default = False
)


def collect_setting_keys_in_use():
    sim_engine_dir = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        '../SimEngine'
    )

    # collect core files
    core_files = []
    for root, dirs, files in os.walk(sim_engine_dir):
        for file in files:
            if file in ['SimSettings.py', 'SimConfig.py']:
                # skip SimSettings.py and SimConfig.py
                continue
            if re.match(r'^.+\.py$', file):
                core_files.append(
                    os.path.join(
                        root,
                        file
                    )
                )

    # identify SimSettings methods
    sim_settings_methods = [
        name for name, _ in inspect.getmembers(
            SimSettings.SimSettings(),
            predicate=inspect.ismethod
        )
    ]

    # collect settings which are referred in core files
    settings_variables = set([])
    setting_keys = set([])
    for file_path in core_files:
        with open(file_path, 'r') as f:
            for line in f:
                # remote all the white spaces and the new line character
                line = line.rstrip()
                if re.match(r'^import', line):
                    # skip import line
                    continue
                elif re.match(r'^\s*#', line):
                    # skip comment line
                    continue
                elif re.search(r'SimSettings', line):
                    if (
                            re.search(r'SimSettings\(\)\.__dict__', line)
                            and
                            re.search(r' for ', line)
                        ):
                        # this line looks like a 'for' statement; skip this line
                        continue
                    settings = re.sub(r'^(.+)=.+SimSettings.+$', r'\1', line)
                    settings = settings.replace(' ', '')
                    settings_variables.add(settings)
                elif (
                        (len(settings_variables) > 0)
                        and
                        re.search('|'.join(settings_variables), line)
                    ):
                    # identify a setting key in in this line
                    pattern = re.compile(
                        '(' + '|'.join(settings_variables) + ')' +
                        '\.(\w+)'
                    )
                    m = re.search(pattern, line)
                    if m is not None:
                        key = m.group(2)
                        if key in sim_settings_methods:
                            # it's class/instance method; skip it
                            continue
                        elif key == '__dict__':
                            # this is not a key; skip it
                            continue
                        elif key == 'run_id':
                            # run_id is not a setting key; ignore this
                            continue
                        else:
                            # add the key referred from a core file
                            setting_keys.add(m.group(2))

    # add exec_minutesPerRun which is found only in SimSettings, which
    # is not processed in the loop above
    setting_keys.add('exec_minutesPerRun')
    return setting_keys


def print_error_and_exit(msg):
    sys.stderr.write(msg)
    sys.exit(1)


if __name__ == '__main__':
    args = parser.parse_args()

    if args.dump_keys is True:
        for key in sorted(list(collect_setting_keys_in_use())):
            print(key)
        sys.exit(0)

    try:
        if args.config_json == '-':
            # read from stdin
            config_json_path = 'STDIN'
            config = json.loads(sys.stdin.read())
        else:
            config_json_path = os.path.abspath(args.config_json)
            with open(config_json_path, 'r') as f:
                config = json.load(f)

    except IOError as e:
        print_error_and_exit(
            'config.json is not found at: {0}'.format(config_json_path)
        )
    except ValueError as e:
        print_error_and_exit('No JSON object could be decoded')

    # start checking...
    # version
    if 'version' not in config:
        print_error_and_exit('unknown config version')
    elif config['version'] != CONFIG_VERSION:
        print_error_and_exit('invalid config version')

    # test keys other than keys for "settings""
    if args.only_settings is True:
        pass
    else:
        for key in CONFIG_KEYS_FOR_RUNSIM + CONFIG_KEYS_FOR_SIMLOG:
            if key not in config:
                print_error_and_exit('{0} setting is missing').format(key)

    # settings
    if 'settings' not in config:
        print_error_and_exit('settings is missing')
    elif 'combination' not in config['settings']:
        print_error_and_exit('settings/combination is missing')
    elif 'regular' not in config['settings']:
        print_error_and_exit('settings/regular is missing')

    keys_in_simulator = collect_setting_keys_in_use()
    keys_in_config = list(config['settings']['combination'].keys())
    keys_in_config += list(config['settings']['regular'].keys())
    for key in keys_in_simulator:
        if key not in keys_in_config:
            print_error_and_exit('"{0}" is missing in settings'.format(key))
    for key in keys_in_config:
        if key not in keys_in_simulator:
            print_error_and_exit('"{0}" is not supported'.format(key))

    print('Looks good!')
