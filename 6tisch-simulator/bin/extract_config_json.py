#!/usr/bin/env python

from __future__ import print_function
import argparse
import json
import os
import sys

if __name__ == '__main__':
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..'))

from SimEngine.SimConfig import SimConfig


def main():
    # command line arguments
    parser = argparse.ArgumentParser(
        description = 'config.json extractor',
        epilog      = """
            This script generates config.json contents out of a log file. The
            log file should have "config" and "simulator.random_seed" lines for
            a target simulation run.
       """
    )
    parser.add_argument(
        'log_file_path',
        help    = 'the path to a log file (.dat)',
        type    = str,
        default = None
    )
    parser.add_argument(
        '-r', '--run_id',
        dest = 'target_run_id',
        help = 'target run_id to extract config.json',
        type = int
    )
    args = parser.parse_args()

    # identify config_line and random_seed
    config_line = None
    random_seed = None
    with open(args.log_file_path, 'r') as f:
        for line in f:
            log = json.loads(line)

            if log['_run_id'] != args.target_run_id:
                continue
            else:
                if log['_type'] == 'config':
                    config_line = log
                elif log['_type'] == 'simulator.random_seed':
                    random_seed = log['value']

                if (
                        (config_line is not None)
                        and
                        (random_seed is not None)
                    ):
                    break

    if (
            (config_line is None)
            or
            (random_seed is None)
        ):
        raise ValueError(
            'cannot find "config" and "random_seed" lines for the target '
            'run_id:{0}.'.format(args.target_run_id)
        )

    # remove unnecessary '_type' element from config_line, which was added to
    # the dictionary of SimSettings object; see SimLog.__init__().
    del config_line['_type']

    # remove '_run_id' and add 'run_id'
    config_line['run_id'] = config_line['_run_id']
    del config_line['_run_id']

    # then, dump a generated config object nicely
    print(json.dumps(
        SimConfig.generate_config(config_line, random_seed),
        indent = 4
    ))


if __name__ == '__main__':
    main()
