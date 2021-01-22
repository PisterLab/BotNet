"""
Tests for random_seed setting
"""
from __future__ import print_function
from __future__ import absolute_import

from builtins import zip
from builtins import range
import hashlib

import pytest

from . import test_utils as u
from SimEngine import SimLog
from SimEngine import SimSettings
from SimEngine import SimConfig

#============================ helpers ==========================================

#============================ fixtures =========================================

@pytest.fixture(params=['random', 1, 10, 100, 'range', 'context'])
def fixture_random_seed(request):
    return request.param

#============================ tests ============================================

def test_random_seed(sim_engine, fixture_random_seed):
    diff_config = {
        'exec_randomSeed'         : fixture_random_seed,
        'exec_numSlotframesPerRun': 100
    }

    log_file_hashes = []

    # compare logs out of 10 runs
    results = []
    for i in range(10):

        sha2     = hashlib.sha256()

        if fixture_random_seed == 'range':
            # ues i for 'exec_randomSeed':
            diff_config['exec_randomSeed'] = i

        engine   = sim_engine(diff_config=diff_config)
        log      = SimLog.SimLog()
        settings = SimSettings.SimSettings()

        # run the simulator
        u.run_until_end(engine)

        # save the log file name and a random seed for later use
        log_file_name = settings.getOutputFile()
        logs = u.read_log_file(
            filter = [SimLog.LOG_SIMULATOR_RANDOM_SEED['type']]
        )
        assert len(logs) == 1
        random_seed = logs[0]['value']

        # destroy singletons for the next run
        engine.connectivity.destroy()
        engine.destroy()
        log.destroy()
        settings.destroy()
        # this is for test purpose only; reset SimConfig._startTime
        SimConfig.SimConfig._startTime = None

        # compute the file hash
        with open(log_file_name, 'r') as f:
            # skip the very first line in the log file, which has
            # 'logDirectory' etnry and it should have a unique value even if a
            # certain integer is specified for 'exec_randSeed'
            f.readline()

            sha2.update(f.read().encode('utf-8'))
            results.append(
                {
                    'log_file_name': log_file_name,
                    'sha256'       : sha2.hexdigest(),
                    'random_seed'  : random_seed
                }
            )

    # collect hash values and print debug messages
    seed_list = []
    hash_list = []
    for entry in results:
        seed_list.append(entry['random_seed'])
        hash_list.append(entry['sha256'])

        # print hash values, which will be printed out when this test fails
        print('{0} {1}'.format(entry['sha256'], entry['log_file_name']))

    # compare hash values and random seeds
    if fixture_random_seed in ['random', 'range', 'context']:
        # different seed values should have been used
        assert (
            sum([i == j for i, j in zip(seed_list[:-1], seed_list[1:])]) == 0
        )
        # hash values shouldn't be the same
        assert (
            sum([i == j for i, j in zip(hash_list[:-1], hash_list[1:])]) == 0
        )
    else:
        # the random seed values are found in the log files should be identical
        assert (
            sum([i != j for i, j in zip(seed_list[:-1], seed_list[1:])]) == 0
        )
        # hash values should be identical as well
        assert (
            sum([i != j for i, j in zip(hash_list[:-1], hash_list[1:])]) == 0
        )
