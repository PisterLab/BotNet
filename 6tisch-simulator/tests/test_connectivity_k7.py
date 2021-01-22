from __future__ import absolute_import
from __future__ import division
from builtins import range
from past.utils import old_div
import datetime as dt
import gzip
import json
import os

import pytest

from . import test_utils as u
import SimEngine.Mote.MoteDefines as d
from SimEngine import SimLog
from SimEngine.Connectivity import (
    Connectivity,
    ConnectivityMatrixBase,
    ConnectivityMatrixK7
)

TRACE_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    '../traces/grenoble.k7.gz'
)

_trace_header = None

def get_trace_header():
    global _trace_header
    if _trace_header is None:
        with gzip.open(TRACE_FILE_PATH, 'r') as tracefile:
            _trace_header = json.loads(tracefile.readline())
    return _trace_header

def get_num_motes():
    header = get_trace_header()
    return header['node_count']

def get_channels():
    header = get_trace_header()
    return header['channels']

def get_trace_duration():
    header = get_trace_header()
    start_time = dt.datetime.strptime(
        header['start_date'],
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    stop_time = dt.datetime.strptime(
        header['stop_date'],
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    return (stop_time - start_time).total_seconds()

def test_free_run(sim_engine):
    """ verify the connectivity matrix for the 'K7' class is as expected """

    num_motes = get_num_motes()

    engine = sim_engine(
        diff_config = {
            'exec_numMotes': get_num_motes(),
            'conn_class'   : 'K7',
            'conn_trace'   : TRACE_FILE_PATH,
            'phy_numChans' : len(get_channels())
        }
    )
    motes  = engine.motes
    matrix = engine.connectivity.matrix

    matrix.dump()

    assert motes[0].dagRoot is True

    for src in range(0, num_motes):
        for dst in range(0, num_motes):
            if src == dst:
                continue
            for channel in d.TSCH_HOPPING_SEQUENCE:
                pdr = matrix.get_pdr(src, dst, channel)
                rssi = matrix.get_rssi(src, dst, channel)
                assert isinstance(pdr, (int, int, float))
                assert isinstance(rssi, (int, int, float))
                assert 0 <= pdr <= 1
                assert ConnectivityMatrixBase.LINK_NONE['rssi'] <= rssi <= 0


@pytest.fixture(params=['short', 'equal', 'long'])
def fixture_test_type(request):
    return request.param

def test_simulation_time(sim_engine, fixture_test_type):
    tsch_slotDuration = 0.010
    numSlotframes = old_div(get_trace_duration(), tsch_slotDuration)
    num_motes = get_num_motes()

    if fixture_test_type == 'short':
        numSlotframes -= 1
    elif fixture_test_type == 'equal':
        pass
    elif fixture_test_type == 'long':
        numSlotframes += 1
    else:
        raise NotImplementedError()

    diff_config = {
        'exec_numSlotframesPerRun': numSlotframes,
        'exec_numMotes'           : num_motes,
        'conn_class'              : 'K7',
        'conn_trace'              : TRACE_FILE_PATH,
        'tsch_slotDuration'       : tsch_slotDuration
    }

    if fixture_test_type == 'long':
        with pytest.raises(ValueError):
            sim_engine(diff_config=diff_config)
        # destroy the ConnectivityK7 instance
        connectivity = Connectivity()
        connectivity.destroy()
    else:
        sim_engine(diff_config=diff_config)

@pytest.fixture(params=[
    'exact_match',
    'all_covered',
    'partly_covered',
    'not_covered'
])
def fixture_channels_coverage_type(request):
    return request.param

def test_check_channels_in_header(
        sim_engine,
        fixture_channels_coverage_type
    ):
    num_motes = get_num_motes()
    channels_in_header = get_channels()
    assert channels_in_header

    tsch_hoppping_sequence_backup = d.TSCH_HOPPING_SEQUENCE
    d.TSCH_HOPPING_SEQUENCE = channels_in_header[:]
    if fixture_channels_coverage_type == 'exact_match':
        # do nothing
        pass
    elif fixture_channels_coverage_type == 'all_covered':
        # remove the first channel in the sequence
        d.TSCH_HOPPING_SEQUENCE.pop(0)
    elif fixture_channels_coverage_type == 'partly_covered':
        # add an invalid channel, which never be listed in the
        # header
        d.TSCH_HOPPING_SEQUENCE.append(-1)
    elif fixture_channels_coverage_type == 'not_covered':
        # put different channels to the hopping sequence from the ones
        # listed in the header
        d.TSCH_HOPPING_SEQUENCE = [x + 10 for x in channels_in_header]
    else:
        raise NotImplementedError()

    diff_config = {
        'exec_numMotes': num_motes,
        'conn_class': 'K7',
        'conn_trace': TRACE_FILE_PATH,
        'phy_numChans': len(d.TSCH_HOPPING_SEQUENCE)
    }
    if fixture_channels_coverage_type in ['partly_covered', 'not_covered']:
        with pytest.raises(ValueError):
            sim_engine(diff_config=diff_config)
        connectivity = Connectivity()
        connectivity.destroy()
    else:
        sim_engine(diff_config=diff_config)

    d.TSCH_HOPPING_SEQUENCE = tsch_hoppping_sequence_backup
