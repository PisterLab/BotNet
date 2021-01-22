from __future__ import absolute_import
from builtins import range
import pytest

from SimEngine import SimLog
from . import test_utils as u
import SimEngine.Mote.MoteDefines as d

# =========================== fixtures ========================================

#@pytest.fixture(params=[2,3,4])
@pytest.fixture(params=[3])
def fixture_exec_numMotes(request):
    return request.param

#@pytest.fixture(params=['up', 'down', 'up-down'])
@pytest.fixture(params=['up-down'])
#@pytest.fixture(params=['up'])
def fixture_data_flow(request):
    return request.param

#@pytest.fixture(params=[False,True])
@pytest.fixture(params=[True])
def fixture_secjoin_enabled(request):
    return request.param

#@pytest.fixture(params=[10, 100, 200])
@pytest.fixture(params=[100])
def fixture_app_pkLength(request):
    return request.param

#@pytest.fixture(params=["PerHopReassembly", "FragmentForwarding"])
@pytest.fixture(params=["FragmentForwarding"])
def fixture_fragmentation(request):
    return request.param

#@pytest.fixture(params=[True, False])
@pytest.fixture(params=[True])
def fixture_ff_vrb_policy_missing_fragment(request):
    return request.param

#@pytest.fixture(params=[True, False])
@pytest.fixture(params=[True])
def fixture_ff_vrb_policy_last_fragment(request):
    return request.param

@pytest.fixture(params=['SFNone', 'MSF'])
def fixture_sf_class(request):
    return request.param

# =========================== helpers =========================================

def check_all_nodes_send_x(motes, x):
    senders = list(set([
        l['_mote_id'] for l in u.read_log_file([SimLog.LOG_TSCH_TXDONE['type']])
        if l['packet']['type'] == x
    ]))
    assert sorted(senders) == sorted([m.id for m in motes])

def check_all_nodes_x(motes, x):
    logs = list(set([l['_mote_id'] for l in u.read_log_file([x])]))
    assert sorted(logs) == sorted([m.id for m in motes])

# === mote

def check_no_packet_drop():
    assert u.read_log_file(['packet_dropped']) == []

def check_neighbor_tables(motes):
    for mote in motes:
        if   mote.id == 0:
            expectedNeighbors = [motes[1].get_mac_addr()]
        elif mote.id == len(motes) -1:
            parent = motes[mote.id - 1]
            expectedNeighbors = [parent.get_mac_addr()]
        else:
            parent = motes[mote.id - 1]
            child = motes[mote.id + 1]
            expectedNeighbors = [parent.get_mac_addr(), child.get_mac_addr()]

        assert sorted(mote.tsch.neighbor_table) == sorted(expectedNeighbors)

# === secjoin

def secjoin_check_all_nodes_joined(motes):
    check_all_nodes_x(motes, SimLog.LOG_SECJOIN_JOINED['type'])

# === app

def count_num_app_rx(appcounter):
    numrx = 0
    for app_rx in u.read_log_file([SimLog.LOG_APP_RX['type']]):
        if app_rx['appcounter'] == appcounter:
            numrx += 1
    assert numrx == 1

# === RPL

def rpl_check_all_node_prefered_parent(motes):
    """ Verify that each mote has a preferred parent """
    for mote in motes:
        if mote.dagRoot:
            continue
        else:
            assert mote.rpl.getPreferredParent() is not None

def rpl_check_all_node_rank(motes):
    """ Verify that each mote has a rank """
    for mote in motes:
        assert mote.rpl.get_rank() is not None

def rpl_check_all_nodes_send_DIOs(motes):
    check_all_nodes_send_x(motes,'DIO')

def rpl_check_all_motes_send_DAOs(motes):
    senders = list(
        set([l['_mote_id']
            for l in u.read_log_file([SimLog.LOG_TSCH_TXDONE['type']])
            if l['packet']['type'] == 'DAO'])
        )
    assert sorted(senders) == sorted([m.id for m in motes if m.id != 0])

def rpl_check_root_parentChildfromDAOs(motes):
    root = motes[0]

    # assuming a linear topology
    expected = {}
    for m in motes:
        if m.id == 0:
            continue
        parent_addr = motes[m.id - 1].get_ipv6_global_addr()
        child_addr = motes[m.id].get_ipv6_global_addr()
        expected[child_addr] = parent_addr

    assert root.rpl.parentChildfromDAOs == expected

# === TSCH

def tsch_check_all_nodes_synced(motes):
    check_all_nodes_x(motes, SimLog.LOG_TSCH_SYNCED['type'])

def tsch_check_all_nodes_send_EBs(motes):
    check_all_nodes_send_x(motes, 'EB')

def tsch_all_nodes_check_dedicated_cell(motes):
    """ Verify that each mote has at least one cell with its preferred parent (TX and/or RX)"""
    for mote in motes:
        if mote.dagRoot:
            continue

        parent = mote.rpl.getPreferredParent()

        # at least one dedicated cell to its preferred parent, which has the TX
        # bit on
        tx_cells = [cell for cell in mote.tsch.get_cells(parent, mote.sf.SLOTFRAME_HANDLE_NEGOTIATED_CELLS) if d.CELLOPTION_TX in cell.options]

        assert len(tx_cells) > 0

# =========================== tests ===========================================

def test_vanilla_scenario(
        sim_engine,
        fixture_exec_numMotes,
        fixture_data_flow,
        fixture_secjoin_enabled,
        fixture_app_pkLength,
        fixture_fragmentation,
        fixture_ff_vrb_policy_missing_fragment,
        fixture_ff_vrb_policy_last_fragment,
        fixture_sf_class,
    ):
    """
    Let the network form, send data packets up and down.
    """

    # initialize the simulator
    fragmentation_ff_discard_vrb_entry_policy = []
    if fixture_ff_vrb_policy_missing_fragment:
        fragmentation_ff_discard_vrb_entry_policy += ['missing_fragment']
    if fixture_ff_vrb_policy_last_fragment:
        fragmentation_ff_discard_vrb_entry_policy += ['last_fragment']
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes':                               fixture_exec_numMotes,
            'exec_numSlotframesPerRun':                    10000,
            'secjoin_enabled':                             fixture_secjoin_enabled,
            'app_pkLength' :                               fixture_app_pkLength,
            'app_pkPeriod':                                0, # disable, will be send by test
            'rpl_daoPeriod':                               60,
            'tsch_probBcast_ebProb'   :                    0.33,
            'fragmentation':                               fixture_fragmentation,
            'fragmentation_ff_discard_vrb_entry_policy':   fragmentation_ff_discard_vrb_entry_policy,
            'sf_class':                                    fixture_sf_class,
            'conn_class':                                  'Linear',
        },
    )

    # === network forms

    # give the network time to form
    u.run_until_asn(sim_engine, 20*60*100)

    # verify no packet was dropped
    #check_no_packet_drop()

    # verify that all nodes are sync'ed
    tsch_check_all_nodes_synced(sim_engine.motes)

    # verify that all nodes are join'ed
    secjoin_check_all_nodes_joined(sim_engine.motes)

    # verify neighbor tables
    check_neighbor_tables(sim_engine.motes)

    # verify that all nodes have acquired rank and preferred parent
    rpl_check_all_node_prefered_parent(sim_engine.motes)
    rpl_check_all_node_rank(sim_engine.motes)

    # verify that all nodes are sending EBs, DIOs and DAOs
    tsch_check_all_nodes_send_EBs(sim_engine.motes)
    rpl_check_all_nodes_send_DIOs(sim_engine.motes)
    rpl_check_all_motes_send_DAOs(sim_engine.motes)

    # verify that root has stored enough DAO information to compute source routes
    rpl_check_root_parentChildfromDAOs(sim_engine.motes)

    # verify that all nodes have a dedicated cell to their parent
    if fixture_sf_class!='SFNone':
        tsch_all_nodes_check_dedicated_cell(sim_engine.motes)

    # === send data up/down

    # appcounter increments at each packet
    appcounter = 0

    # pick a "datamote" which will send/receive data
    datamote = sim_engine.motes[-1] # pick furthest mote

    # get the DAG root
    dagroot  = sim_engine.motes[sim_engine.DAGROOT_ID]

    # verify no packets yet received by root
    assert len(u.read_log_file([SimLog.LOG_APP_RX['type']])) == 0

    # send packets upstream (datamote->root)
    if fixture_data_flow.find("up") != -1:

        for _ in range(10):

            # inject data at the datamote
            datamote.app._send_a_single_packet()

            # give the data time to reach the root
            u.run_until_asn(sim_engine, sim_engine.getAsn() + 10000)

            # verify datamote got exactly one packet
            #count_num_app_rx(appcounter)

            # increment appcounter
            appcounter += 1

    # send data downstream (root->datamote)
    if fixture_data_flow.find("down") != -1:

        for _ in range(10):

            # inject data at the root
            dagroot.app._send_ack(datamote.id)

            # give the data time to reach the datamote
            u.run_until_asn(sim_engine, sim_engine.getAsn() + 10000)

            # verify datamote got exactly one packet
            #count_num_app_rx(appcounter)

            # increment appcounter
            appcounter += 1

    # === checks

    # verify no packet was dropped
    #check_no_packet_drop()
