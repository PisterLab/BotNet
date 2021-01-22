from __future__ import absolute_import
from __future__ import division
from past.utils import old_div
import json

import pytest

from . import test_utils as u
from SimEngine.SimConfig import SimConfig
from SimEngine.SimLog import SimLog

def test_generate_config(sim_engine):
    sim_engine = sim_engine()
    settings = sim_engine.settings

    # prepare expected_config
    with open(u.CONFIG_FILE_PATH, 'r') as f:
        expected_config = json.load(f)

    # adjust 'regular' field:
    # put first values in combination settings to 'regular' field as well as
    # empty the combination field
    if 'combination' in expected_config['settings']:
        comb_keys = list(expected_config['settings']['combination'].keys())

        while len(comb_keys) > 0:
            key = comb_keys.pop(0)
            value = expected_config['settings']['combination'][key][0]
            assert key  not in expected_config['settings']['regular']
            expected_config['settings']['regular'][key] = value
            del expected_config['settings']['combination'][key]
        expected_config
    # make 'exec_numMotes' a combination setting so that a directory for a log
    # file is properly made. SimSettings needs one combination at least. See
    # SimSettings.getOutputFile()
    expected_config['settings']['combination'] = {
        'exec_numMotes': [
            expected_config['settings']['regular']['exec_numMotes']
        ]
    }
    del expected_config['settings']['regular']['exec_numMotes']

    # adjust 'post' field
    expected_config['post'] = []

    # adjust 'log' related fields
    expected_config['log_directory_name'] = 'startTime'
    expected_config['logging'] = 'all'

    # make sure the 'execution' field is fine
    expected_config['execution']['numCPUs'] == 1
    expected_config['execution']['numRuns'] == 1

    # set a random value
    expected_config['settings']['regular']['exec_randomSeed'] = (
        sim_engine.random_seed
    )

    # ready to test
    config = SimConfig.generate_config(
        settings_dict = settings.__dict__,
        random_seed   = sim_engine.random_seed
    )
    assert config == expected_config

@pytest.fixture(params=[1000, None])
def exec_num_slotframes_per_run(request):
    return request.param


@pytest.fixture(params=[10, None])
def exec_minutes_per_run(request):
    return request.param

def test_exec_minutes_per_run(
        sim_engine,
        exec_num_slotframes_per_run,
        exec_minutes_per_run
    ):
    diff_config = {
        'exec_numSlotframesPerRun': exec_num_slotframes_per_run,
        'exec_minutesPerRun'      : exec_minutes_per_run,
        'tsch_slotDuration'       : 0.01,
        'tsch_slotframeLength'    : 100,
        'exec_numMotes'           : 1
    }
    if (
            (exec_num_slotframes_per_run and exec_minutes_per_run)
            or
            ((not exec_num_slotframes_per_run) and (not exec_minutes_per_run))
        ):
        with pytest.raises(ValueError):
            sim_engine = sim_engine(diff_config)
        # for teardown
        sim_engine = sim_engine(diff_config={})
    else:
        sim_engine = sim_engine(diff_config)
        assert isinstance(sim_engine.settings.exec_numSlotframesPerRun, int)
        assert sim_engine.settings.exec_minutesPerRun is None

        u.run_until_end(sim_engine)
        if exec_num_slotframes_per_run:
            end_asn = (
                diff_config['tsch_slotframeLength'] *
                exec_num_slotframes_per_run
            )
        else:
            assert exec_minutes_per_run
            end_asn = (
                old_div(exec_minutes_per_run * 60, diff_config['tsch_slotDuration'])
            )
        assert sim_engine.getAsn() == end_asn
