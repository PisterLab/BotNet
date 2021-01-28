from __future__ import absolute_import
import pytest

from . import test_utils as u
import SimEngine
import SimEngine.Mote.MoteDefines as d


APP = ['AppPeriodic', 'AppBurst']
@pytest.fixture(params=APP)
def app(request):
    return request.param

@pytest.fixture(params=[0, 60])
def fixture_dao_period(request):
    return request.param

def test_app_upstream(
        sim_engine,
        app,
        fixture_dao_period
    ):

    # at least one app packet should be observed during the simulation

    sim_engine = sim_engine(
        {
            'exec_numMotes'                            : 2,
            'exec_numSlotframesPerRun'                 : 1000,
            'sf_class'                                 : 'SFNone',
            'conn_class'                               : 'Linear',
            'secjoin_enabled'                          : False,
            'app'                                      : app,
            'app_pkPeriod'                             : 2,
            'app_pkPeriodVar'                          : 0,
            'app_pkLength'                             : 90,
            'app_burstTimestamp'                       : 1,
            'app_burstNumPackets'                      : 5,
            'rpl_daoPeriod'                            : fixture_dao_period
        }
    )

    # give the network time to form
    u.run_until_end(sim_engine)

    # the number of 'app.tx' is the same as the number of generated packets.
    logs = u.read_log_file(filter=['app.tx'])

    # five packets should be generated per application
    assert len(logs) > 0

def test_app_burst(sim_engine):
    num_burst_packets = 2
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'           : 2,
            'app'                     : 'AppBurst',
            'app_burstTimestamp'      : 1,
            'app_burstNumPackets'     : num_burst_packets,
            'rpl_daoPeriod'           : 1,
            'conn_class'              : 'Linear',
            'tsch_keep_alive_interval': False,
        }
    )

    u.run_until_end(sim_engine)

    # we should see only two app.tx (as many as num_burst_packets) by
    # mote_1
    logs = u.read_log_file(filter=['app.tx'])
    logs = [log for log in logs if log['_mote_id']==1]
    assert len(logs) == num_burst_packets
