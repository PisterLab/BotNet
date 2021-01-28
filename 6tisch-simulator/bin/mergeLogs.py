#!/usr/bin/python
"""
This script merges log files under 'hostname' based log directory
"""
from __future__ import print_function

# =========================== imports =========================================
from builtins import zip
from builtins import input
from builtins import range
import argparse
import filecmp
import json
import os
import re
import shutil
import time

# =========================== helpers =========================================


def parseCliParams():
    parser = argparse.ArgumentParser(
        formatter_class = argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '-l', '-logRootDir',
        dest            = 'logRootDir',
        action          = 'store',
        default         = './simData',
        help            = 'Location of the root directory for log data.'
    )

    parser.add_argument(
        '-o', '--output-dir',
        dest            = 'output_dir',
        default         = None,
        help            = 'Location of the output directory for merged log data.'
    )

    parser.add_argument(
        '-d', '--dry-run',
        dest            = 'dryRun',
        action          = 'store_true',
        default         = False,
        help            = 'Run without any change to the file system'
    )

    parser.add_argument(
        '-k', '--keep-src',
        dest            = 'keepSource',
        action          = 'store_true',
        default         = False,
        help            = 'Not remove source files/directories after the merger'
    )

    parser.add_argument(
        '-y', '--yes',
        dest            = 'noPrompt',
        action          = 'store_true',
        default         = False,
        help            = 'Run without user input (confirmation)'
    )

    cliparams      = parser.parse_args()
    return cliparams.__dict__


def getTargetSubDirs(logRootDir):
    # scan the log directory to identify sub-directories to handle, which are
    # hostname-based sub-directries. A directory named with startTime, e.g.,
    # "20180509-103132", is not recognized as a target sub-directory.
    targetSubDirs    = []

    # startTime is in a format of "YYYYmmdd-HHMMSS", 8 digits and 6 digites
    # connected with '-'.
    startTimePattern = re.compile('^\d{8}-\d{6}$')

    for entryName in  os.listdir(logRootDir):
        subdirPath = os.path.join(logRootDir, entryName)
        if (
                os.path.isdir(subdirPath)
                and
                (not startTimePattern.match(entryName))
           ):
            targetSubDirs.append(subdirPath)

    # sanity check: make sure all the sub-directories have the same file
    # entries and the same config.json
    i_list = list(range(0, len(targetSubDirs) - 1))
    j_list = list(range(1, len(targetSubDirs)))
    for (i, j) in zip(i_list, j_list):
        cmp = filecmp.dircmp(targetSubDirs[i], targetSubDirs[j])

        # check the two sub-directories has the same file entries
        if (
                (len(cmp.left_only)  > 0)
                or
                (len(cmp.right_only) > 0)
           ):
            raise ValueError(
                '{0} and {1} should have the same file entries'.format(
                    targetSubDirs[i],
                    targetSubDirs[j]
                )
            )

        # check the two sub-directories has the identical config.json
        if 'config.json' not in cmp.same_files:
            raise ValueError(
                '{0} and {1} should have the identical config.json'.format(
                    targetSubDirs[i],
                    targetSubDirs[j]
                )
            )

    return targetSubDirs


def getTotalTargetFileNum(targetSubDirs):
    returnVal = 0

    # count all .dat files
    for f in targetSubDirs:
        data_files = [file for file in os.listdir(f) if re.match('^.+\.dat$', file) != None]
        returnVal += len(data_files)

    # add one for config.json
    returnVal +=1

    return returnVal


def mergeLogFiles(logDir, targetSubDirs, dryRun):

    # get the total number of files to be processes
    total_target_file_num    = getTotalTargetFileNum(targetSubDirs)
    total_processed_file_num = 0

    # make a new log directory
    print('mkdir {0}'.format(logDir))
    if not dryRun:
        os.mkdir(logDir)

    cpu_id_offset = None
    run_id_offset = None

    # copy config.json under logDir
    config_json_path = os.path.join(
        targetSubDirs[0],
        'config.json'
    )
    print('[{0:3d}%] copying config.json to {1}'.format(
        int(float(total_processed_file_num) / total_target_file_num * 100),
        logDir
    ))
    if not dryRun:
        shutil.copy(config_json_path, logDir)
    total_processed_file_num += 1

    cpu_id_offset = 0
    run_id_offset = 0
    cpu_id_list   = []
    run_id_list   = []
    skipped_lines = []

    for targetDir in targetSubDirs:

        cpu_id_offset += len(cpu_id_list)
        run_id_offset += len(run_id_list)
        cpu_id_list    = []
        run_id_list    = []

        for fileName in os.listdir(targetDir):
            # merge only *.dat files
            if re.match('^.+\.dat$', fileName) == None:
                continue

            # identify input file and output file
            infile_path  = os.path.join(targetDir, fileName)
            outfile_path = os.path.join(logDir, fileName)

            # print progress
            print('[{0:3d}%] merging {1} to {2}'.format(
                int(float(total_processed_file_num) / total_target_file_num * 100),
                infile_path,
                outfile_path
            ))

            if not dryRun:
                # actual merger happens here
                with open(infile_path, 'r') as infile:
                    with open(outfile_path, 'a') as outfile:

                        for line in infile:
                            # read a log line
                            try:
                                log = json.loads(line)
                            except ValueError:
                                # input line cannot be parsed as a json
                                # string. it may be corrupted
                                skipped_lines.append((infile_path, line))
                                continue

                            # collect cpuID and _runid that are used to compute
                            # cpu_id_offset and run_id_offset
                            if log['_type'] == 'config':
                                if not log['cpuID'] in cpu_id_list:
                                    cpu_id_list.append(log['cpuID'])

                                if not log['_run_id'] in run_id_list:
                                    run_id_list.append(log['_run_id'])

                            # update cpuID and _run_id fields accordingly
                            if 'cpuID' in log:
                                log['cpuID'] += cpu_id_offset
                            if '_run_id' in log:
                                log['_run_id'] += run_id_offset

                            # write the log line to outfile
                            outfile.write(json.dumps(log) + "\n")

            total_processed_file_num += 1

    assert total_processed_file_num == total_target_file_num
    print('[100%] merger done')

    if len(skipped_lines) > 0:
        # we have skipped lines; dump them into a file
        skipped_lines_file = os.path.join(logDir, 'skipped-lines.txt')
        print('We have log lines which are not parsed correctly.')
        print('You can find them in {0}'.format(skipped_lines_file))
        with open(skipped_lines_file, 'w') as f:
            for (file_name, line) in skipped_lines:
                f.write('{0}, {1}'.format(file_name, line))

# =========================== main ============================================


def main():
    # cli params
    cliparams = parseCliParams()
    assert cliparams['logRootDir']

    # get target sub-directories
    targetSubDirs = getTargetSubDirs(cliparams['logRootDir'])
    if len(targetSubDirs) == 0:
        print('No log files to merge under {0}'.format(cliparams['logRootDir']))
        exit(0)

    if cliparams['output_dir']:
        if os.path.exists(cliparams['output_dir']):
            print('{0} exists already; specify a different one'.format(
                cliparams['output_dir']
            ))
            exit(1)
        else:
            logDir = os.path.abspath(cliparams['output_dir'])
    else:
        # create a new sub-directory where merged log files are stored.
        logDir = os.path.join(
            cliparams['logRootDir'],
            time.strftime("%Y%m%d-%H%M%S")
        )

    # get user's confirmation
    print('Log files under the following directories will be merged:')
    for sub_dir in sorted(targetSubDirs):
        print('  {0}'.format(sub_dir))

    if cliparams['keepSource'] is False:
        print('These directories will be removed.')

    print('A new log directory is: {0}'.format(logDir))

    if cliparams['noPrompt'] is False:
        print('Hit "return" to proceed')
        input()

    # create new log files under logDir which have all the log data under the
    # target sub-directories.
    mergeLogFiles(logDir, targetSubDirs, cliparams['dryRun'])

    # remove target sub-directories
    if cliparams['keepSource'] is False:
        for subdir in targetSubDirs:
            print('removing {0}'.format(subdir))
            if not cliparams['dryRun']:
                shutil.rmtree(subdir)

if __name__ == '__main__':
    main()
