from __future__ import absolute_import
from builtins import range
import pytest

from . import test_utils as u
import SimEngine.Mote.MoteDefines as d
from SimEngine import SimConfig

#============================ helpers =========================================

#============================ tests ===========================================

#=== test to verify sim_engine is created/destroyed well

def test_sim_engine_created(sim_engine, repeat4times):
    pass

#=== test to verify sim_engine is created/init/destroyed well

def test_sim_engine_created_and_init(sim_engine, repeat4times):
    s = sim_engine(
        diff_config = {
            'exec_numMotes': 1,
        }
    )

#=== exception during initialization

def test_exception_at_intialization(sim_engine, repeat4times):
    with pytest.raises(TypeError):
        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes': 'dummy', # 'dummy' not int, causes exception
            }
        )

#=== runtime exception propagates past run_until_asn()

class MyException(Exception):
    pass

def _raiseException():
    raise MyException()

def test_exception_at_runtime(sim_engine, repeat4times):
    """test if an exception raised in a SimEngine thread is propagated here

    Run a simulation in one slotframe
    """
    sim_engine = sim_engine()
    sim_engine.scheduleAtAsn(
        asn             = 10,
        cb              = _raiseException,
        uniqueTag       = ('engine','_raiseException'),
        intraSlotOrder  = 1,
    )

    with pytest.raises(MyException):
        u.run_until_asn(
            sim_engine,
            target_asn = 20, # past the _raiseException event
        )

#=== testing force_initial_routing_and_scheduling_state options

FORCE_INITIAL_ROUTING_AND_SCHEDULING_STATE = [False]
@pytest.fixture(params=FORCE_INITIAL_ROUTING_AND_SCHEDULING_STATE)
def force_initial_routing_and_scheduling_state(request):
    return request.param

def test_instantiation(sim_engine, force_initial_routing_and_scheduling_state, repeat4times):
    sim_engine = sim_engine(
        diff_config                                   = {},
        force_initial_routing_and_scheduling_state    = force_initial_routing_and_scheduling_state,
    )

#=== verify forced initial scheduling state
def test_initial_scheduling_state(sim_engine):
    sim_engine = sim_engine(
        diff_config                                   = {
            'exec_numMotes':                            10
        },
        force_initial_routing_and_scheduling_state    = True
    )

    # Each mote should have one TX/RX/SHARED cell and one TX dedicated cell to
    # its parent. In this sense, a mote has the same number of RX dedicated
    # cells as its children. We'll have a linear topology with
    # force_initial_routing_and_scheduling_state True, each mote except for the
    # root and the leaf has one TX cell and one RX cell. The root has one RX
    # cell. The leaf has one TX cell.
    for mote in reversed(sim_engine.motes):

        # check shared cell
        assert (
            len(
                [cell for cell in mote.tsch.get_cells(None) if cell.options == [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]]
            ) == 1
        )

        # check dedicated cell
        # FIXME: what is the best way to get mote instance by mote_id?
        if mote.rpl.getPreferredParent() == None:
            continue

        parent = sim_engine.get_mote_by_mac_addr(mote.rpl.getPreferredParent())
        # "mote" has one TX to its parent
        assert (
            len(
                [cell for cell in mote.tsch.get_cells(parent.get_mac_addr()) if cell.options == [d.CELLOPTION_TX]]
            ) == 1
        )
        # parent of "mote" one RX to "mote"
        assert (
            len(
                [cell for cell in parent.tsch.get_cells(mote.get_mac_addr()) if cell.options == [d.CELLOPTION_RX]]
            ) == 1
        )

#=== verify default configs from bin/config.json are loaded correctly

def test_sim_config(sim_engine, repeat4times):

    sim_config  = SimConfig.SimConfig(u.CONFIG_FILE_PATH)

    sim_engine = sim_engine()
    for (k,v) in list(sim_config.config['settings']['regular'].items()):
        assert getattr(sim_engine.settings,k) == v

#=== test that run_until_asn() works

def test_run_until_asn(sim_engine, repeat4times):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes':            1,
            'exec_numSlotframesPerRun': 1,
        }
    )

    assert sim_engine.getAsn() == 0

    for target_asn in range(1,10,5):
        u.run_until_asn(
            sim_engine,
            target_asn = target_asn,
        )
        assert sim_engine.getAsn() == target_asn

#=== test that run_until_end() works

@pytest.fixture(params=[100, 200, 1000])
def num_slotframes(request):
    return request.param

@pytest.fixture(params=[100, 101])
def slotframe_length(request):
    return request.param

def test_run_until_end(sim_engine, num_slotframes, slotframe_length):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numSlotframesPerRun': num_slotframes,
            'tsch_slotframeLength':     slotframe_length
        }
    )

    u.run_until_end(sim_engine)

    assert sim_engine.getAsn() == slotframe_length * num_slotframes

#=== test that run_until_everyone_joined() works

@pytest.fixture(params=[2, 5])
def exec_num_motes(request):
    return request.param

@pytest.fixture(params=[True, False])
def secjoin_enabled(request):
    return request.param

def test_run_until_everyone_joined(
        sim_engine,
        exec_num_motes,
        secjoin_enabled
    ):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'           : exec_num_motes,
            'secjoin_enabled'         : secjoin_enabled,
            'exec_numSlotframesPerRun': 10000,
            'app_pkPeriod'            :  0,
            'conn_class'              : 'Linear',
            'tsch_keep_alive_interval': 0
        }
    )

    # everyone should have not been joined yet
    assert (
        len([m for m in sim_engine.motes if m.secjoin.getIsJoined() is False]) > 0
    )

    u.run_until_everyone_joined(sim_engine)

    # everyone should have been joined
    assert (
        len([m for m in sim_engine.motes if m.secjoin.getIsJoined() is False]) == 0
    )

    # expect the simulator has the remaining time; that is, the simulator
    # should not be paused by run_until_end() called inside of
    # run_until_everyone_joined()
    slotframe_length = sim_engine.settings.tsch_slotframeLength
    num_slotframes   = sim_engine.settings.exec_numSlotframesPerRun
    asn_at_end       = slotframe_length * num_slotframes
    assert sim_engine.getAsn() < asn_at_end
