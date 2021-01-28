from __future__ import absolute_import
from __future__ import division
from builtins import zip
from past.utils import old_div
import pytest

from . import test_utils as u
import SimEngine.Mote.MoteDefines as d
from SimEngine import SimLog


@pytest.fixture(params=[True, False])
def with_keep_alive(request):
    return request.param


def test_tsch_clock(sim_engine, with_keep_alive):
    diff_config = {
        'exec_numMotes'           : 3,
        'app_pkPeriod'            : 0,
        'app_pkPeriodVar'         : 0,
        'tsch_probBcast_ebProb'   : 0,
        'rpl_daoPeriod'           : 0,
        'exec_numSlotframesPerRun': 100,
        'conn_class'              : 'Linear'
    }
    if with_keep_alive is True:
        diff_config['tsch_keep_alive_interval'] = 10
    else:
        diff_config['tsch_keep_alive_interval'] = 0
    diff_config['exec_randomSeed'] = 7263092949079992026
    sim_engine = sim_engine(
        diff_config                                = diff_config,
        force_initial_routing_and_scheduling_state = True
    )

    log_type_clock_diff = 'clock_diff'
    sim_log = SimLog.SimLog()

    # static values
    macTsRxWait = 0.00222 # 2,220 usec defined for 2.4 GHz by IEEE 802.15.4-2015

    # shorthands
    root             = sim_engine.motes[0]
    hop_1            = sim_engine.motes[1]
    hop_2            = sim_engine.motes[2]
    slot_duration    = sim_engine.settings.tsch_slotDuration
    slotframe_length = sim_engine.settings.tsch_slotframeLength
    max_drift        = sim_engine.settings.tsch_clock_max_drift_ppm
    clock_interval   = 1.0 / sim_engine.settings.tsch_clock_frequency
    guard_time       = (old_div(macTsRxWait, 2)) - (2 * clock_interval)

    def _check_and_log_clock_drift():
        # without keep-alive, difference between the two clocks is
        # getting bigger and bigger. but, it should be within
        # -max_drift*2 and +max_drift*2 with offset in the range
        # between 0 and clock_interval

        diff_1 = hop_1.tsch.clock.get_drift() - root.tsch.clock.get_drift()
        diff_2 = hop_2.tsch.clock.get_drift() - hop_1.tsch.clock.get_drift()
        elapsed_time = sim_engine.getAsn() * slot_duration
        lower_bound_drift = (
            elapsed_time * (-1 * max_drift * 2) + 0
        )
        upper_bound_drift = (
            elapsed_time * (+1 * max_drift * 2) + clock_interval
        )
        assert lower_bound_drift < diff_1
        assert diff_1 < upper_bound_drift

        assert lower_bound_drift < diff_2
        assert diff_2 < upper_bound_drift

        if with_keep_alive:
            assert abs(diff_1) < guard_time
            assert abs(diff_2) < guard_time

        # custom log
        for mote_id, diff in zip([hop_1.id, hop_2.id], [diff_1, diff_2]):
            sim_log.log(
                {'type': log_type_clock_diff, 'keys': ['_mote_id', 'value']},
                {'_mote_id': mote_id, 'value': diff}
            )
        _schedule_clock_drift_checking_and_logging()

    def _schedule_clock_drift_checking_and_logging():
        sim_engine.scheduleAtAsn(
            asn            = sim_engine.getAsn() + (1.0 / slot_duration),
            cb             = _check_and_log_clock_drift,
            uniqueTag      = 'check_and_log_clock_drift',
            intraSlotOrder = d.INTRASLOTORDER_ADMINTASKS
        )

    _schedule_clock_drift_checking_and_logging()
    u.run_until_end(sim_engine)

    keep_alive_logs = [
        log for log in u.read_log_file([SimLog.LOG_TSCH_TXDONE['type']]) if (
            log['packet']['type'] == d.PKT_TYPE_KEEP_ALIVE
        )
    ]

    if with_keep_alive is True:
        assert len(keep_alive_logs) > 0
    else:
        assert len(keep_alive_logs) == 0
