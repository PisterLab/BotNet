#!/usr/bin/python
"""
\brief Entry point to the simulator. Starts a batch of simulations concurrently.
\author Thomas Watteyne <watteyne@eecs.berkeley.edu>
\author Malisa Vucinic <malishav@gmail.com>
"""
from __future__ import print_function

# =========================== adjust path =====================================

from builtins import zip
from builtins import range
import os
import platform
import sys

if __name__ == '__main__':
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..'))

# =========================== imports =========================================

import time
import subprocess
import itertools
import threading
import math
import multiprocessing
import argparse
import json
import glob
import shutil

from SimEngine import SimConfig,   \
                      SimEngine,   \
                      SimLog, \
                      SimSettings, \
                      Connectivity

# =========================== helpers =========================================

def parseCliParams():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--config',
        dest       = 'config',
        action     = 'store',
        default    = 'config.json',
        help       = 'Location of the configuration file.',
    )
    cliparams      = parser.parse_args()
    return cliparams.__dict__

def getTemplogFileName(cpuID, pid):
    hostname = platform.uname()[1]
    return '{0}-pid{1}-cpu{2}.templog'.format(hostname, pid, cpuID)

def printOrLog(cpuID, pid, output, verbose):
    assert cpuID is not None

    if not verbose:
        with open(getTemplogFileName(cpuID, pid), 'w') as f:
            f.write(output)
    else:
        print(output)

def runSimCombinations(params):
    """
    Runs simulations for all combinations of simulation settings.
    This function may run independently on different CPUs.
    """

    cpuID              = params['cpuID']
    pid                = params['pid']
    numRuns            = params['numRuns']
    first_run          = params['first_run']
    verbose            = params['verbose']
    config_data        = params['config_data']

    simconfig = SimConfig.SimConfig(configdata=config_data)

    # record simulation start time
    simStartTime        = time.time()

    # compute all the simulation parameter combinations
    combinationKeys     = list(simconfig.settings.combination.keys())
    simParams           = []
    for p in itertools.product(*[simconfig.settings.combination[k] for k in combinationKeys]):
        simParam = {}
        for (k, v) in zip(combinationKeys, p):
            simParam[k] = v
        for (k, v) in list(simconfig.settings.regular.items()):
            if k not in simParam:
                simParam[k] = v
        simParams      += [simParam]

    # run a simulation for each set of simParams
    for (simParamNum, simParam) in enumerate(simParams):

        # run the simulation runs
        for run_id in range(first_run, first_run+numRuns):

            # printOrLog
            output  = 'parameters {0}/{1}, run {2}/{3}'.format(
               simParamNum+1,
               len(simParams),
               run_id+1-first_run,
               numRuns
            )
            printOrLog(cpuID, pid, output, verbose)

            # create singletons
            settings         = SimSettings.SimSettings(cpuID=cpuID, run_id=run_id, **simParam)
            settings.setLogDirectory(simconfig.get_log_directory_name())
            settings.setCombinationKeys(combinationKeys)
            simlog           = SimLog.SimLog()
            simlog.set_log_filters(simconfig.logging)
            simengine        = SimEngine.SimEngine(run_id=run_id, verbose=verbose)


            # start simulation run
            simengine.start()

            # wait for simulation run to end
            simengine.join()

            # destroy singletons
            simlog.destroy()
            simengine.destroy()
            Connectivity.Connectivity().destroy()
            settings.destroy() # destroy last, Connectivity needs it

        # printOrLog
        output  = 'simulation ended after {0:.0f}s ({1} runs).'.format(
            time.time()-simStartTime,
            numRuns * len(simParams)
        )
        printOrLog(cpuID, pid, output, verbose)

keep_printing_progress = True
def printProgressPerCpu(cpuIDs, pid, clear_console=True):
    while keep_printing_progress:
        time.sleep(1)
        output     = []
        for cpuID in cpuIDs:
            try:
                with open(getTemplogFileName(cpuID, pid), 'r') as f:
                    output += ['[cpu {0}] {1}'.format(cpuID, f.read())]
            except IOError:
                output += ['[cpu {0}] no info (yet?)'.format(cpuID)]
        allDone = True
        for line in output:
            if line.count('ended') == 0:
                allDone = False
        output = '\n'.join(output)
        if clear_console:
            os.system('cls' if os.name == 'nt' else 'clear')
        print(output)
        if allDone:
            break

def merge_output_files(folder_path):
    """
    Read the dataset folders and merge the datasets (usefull when using multiple CPUs).
    :param string folder_path:
    """

    for subfolder in os.listdir(folder_path):
        # subfolder could have '[' in its name, which is a special character
        # for glob. This needs to be escaped.
        file_path_list = sorted(
            glob.glob(
                os.path.join(
                    folder_path,
                    subfolder.replace('[', '[[]'),
                    'output_cpu*.dat'
                )
            )
        )

        # read files and concatenate results
        with open(os.path.join(folder_path, subfolder + ".dat"), 'w') as outputfile:
            for file_path in file_path_list:
                with open(file_path, 'r') as inputfile:
                    config = json.loads(inputfile.readline())
                    outputfile.write(json.dumps(config) + "\n")
                    outputfile.write(inputfile.read())
        shutil.rmtree(os.path.join(folder_path, subfolder))

# =========================== main ============================================

def main():
    
    #=== initialize
    
    # cli params
    cliparams = parseCliParams()

    # sim config
    simconfig = SimConfig.SimConfig(configfile=cliparams['config'])
    assert simconfig.version == 0

    #=== run simulations

    # decide number of CPUs to run on
    multiprocessing.freeze_support()
    max_numCPUs = multiprocessing.cpu_count()
    if simconfig.execution.numCPUs == -1:
        numCPUs = max_numCPUs
    else:
        numCPUs = simconfig.execution.numCPUs
    assert numCPUs <= max_numCPUs

    if numCPUs == 1:
        # run on single CPU

        runSimCombinations({
            'cpuID':              0,
            'pid':                os.getpid(),
            'numRuns':            simconfig.execution.numRuns,
            'first_run':          0,
            'verbose':            True,
            'config_data':        simconfig.get_config_data()
        })

    else:
        # distribute runs on different CPUs
        runsPerCPU = [
            int(
                math.floor(float(simconfig.execution.numRuns) / float(numCPUs))
            )
        ]*numCPUs
        idx         = 0
        while sum(runsPerCPU) < simconfig.execution.numRuns:
            runsPerCPU[idx] += 1
            idx              += 1

        # distribute run ids on different CPUs (transform runsPerCPU into a list of tuples)
        first_run = 0
        for cpuID in range(numCPUs):
            runs = runsPerCPU[cpuID]
            runsPerCPU[cpuID] = (runs, first_run)
            first_run += runs

        # print progress, wait until done
        cpuIDs                = [i for i in range(numCPUs)]
        if simconfig.log_directory_name == 'hostname':
            # We assume the simulator run over a cluster system when
            # 'log_directory_name' is 'hostname'. Under a cluster system, we
            # disable "clear" on console because it could cause "'unknown': I
            # need something more specific." error.
            clear_console = False
        else:
            clear_console = True
        print_progress_thread = threading.Thread(
            target = printProgressPerCpu,
            args   = (cpuIDs, os.getpid(), clear_console)
        )

        print_progress_thread.start()

        # wait for the thread ready
        while print_progress_thread.is_alive() == False:
            time.sleep(0.5)

        # start simulations
        pool = multiprocessing.Pool(numCPUs)
        async_result = pool.map_async(
            runSimCombinations,
            [
                {
                    'cpuID':              cpuID,
                    'pid':                os.getpid(),
                    'numRuns':            runs,
                    'first_run':          first_run,
                    'verbose':            False,
                    'config_data':        simconfig.get_config_data()
                } for [cpuID, (runs, first_run)] in enumerate(runsPerCPU)
            ]
        )

        # get() raises an exception raised by a thread if any
        try:
            async_result.get()
        except Exception:
            raise
        finally:
            # stop print_proress_thread if it's alive
            if print_progress_thread.is_alive():
                global keep_printing_progress
                keep_printing_progress = False
                print_progress_thread.join()

        # cleanup
        hostname = platform.uname()[1]
        for i in range(numCPUs):
            os.remove(getTemplogFileName(i, os.getpid()))

    # merge output files
    folder_path = os.path.join('simData', simconfig.get_log_directory_name())
    merge_output_files(folder_path)

    # copy config file into output directory
    with open(os.path.join(folder_path, 'config.json'), 'w') as f:
        f.write(simconfig.get_config_data())

    #=== post-simulation actions

    if simconfig.log_directory_name == 'hostname':
        # We assume the simulator run over a cluster system when
        # 'log_directory_name' is 'hostname'. Under a cluster system, we
        # disable post actions. Users should perform post actions manually
        # after merging log files by mergeLogs.py.
        pass
    else:
        for c in simconfig.post:
            print('calling "{0}"'.format(c))
            rc = subprocess.call(c, shell=True)
            assert rc==0

if __name__ == '__main__':
    main()
