"""
Test for TSCH layer
"""
from __future__ import absolute_import
from __future__ import division

from builtins import zip
from builtins import range
from past.utils import old_div
import copy
import pytest
import types

from . import test_utils as u
import SimEngine.Mote.MoteDefines as d
from SimEngine import SimLog
from SimEngine.Mote import tsch

# frame_type having "True" in "first_enqueuing" can be enqueued to TX queue
# even if the queue is full.
@pytest.mark.parametrize("frame_type", [
    d.PKT_TYPE_DATA,
    d.PKT_TYPE_FRAG,
    d.PKT_TYPE_JOIN_REQUEST,
    d.PKT_TYPE_JOIN_RESPONSE,
    # not DIO (generetaed by TSCH directly)
    d.PKT_TYPE_DAO,
    # not EB (generetaed by tsch directly)
    d.PKT_TYPE_SIXP,
])
def test_enqueue_under_full_tx_queue(sim_engine,frame_type):
    """
    Test Tsch.enqueue(self) under the situation when TX queue is full
    """
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes':                         3,
        },
        force_initial_routing_and_scheduling_state = True
    )

    root = sim_engine.motes[0]
    hop1 = sim_engine.motes[1]
    hop2 = sim_engine.motes[2]

    # fill the TX queue with dummy frames
    dummy_frame = {'type': 'dummy_frame_type'}
    for _ in range(0, hop1.tsch.txQueueSize):
        hop1.tsch.txQueue.append(dummy_frame)
    assert len(hop1.tsch.txQueue) == hop1.tsch.txQueueSize

    # prepare an additional frame
    test_frame = {
        'type': frame_type,
        'mac': {
            'srcMac': hop1.get_mac_addr(),
            'dstMac': root.get_mac_addr()
        }
    }

    # make sure that queuing that frame fails
    assert hop1.tsch.enqueue(test_frame) == False

def test_enqueue_with_priority(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )
    mote = sim_engine.motes[0]

    # make sure the TX queue is empty now
    assert not mote.tsch.txQueue

    # prepare the base dummy packet
    base_dummy_packet = {
        'type': d.PKT_TYPE_DATA,
        'mac': {
            'srcMac': mote.get_mac_addr(),
            'dstMac': d.BROADCAST_ADDRESS
        }
    }

    # put one normal packet to the TX queue
    normal_packet = copy.deepcopy(base_dummy_packet)
    normal_packet['seq'] = 1
    mote.tsch.enqueue(normal_packet, priority=False)
    assert len(mote.tsch.txQueue) == 1

    # put one priority packet
    priority_packet = copy.deepcopy(base_dummy_packet)
    priority_packet['seq'] = 2
    mote.tsch.enqueue(priority_packet, priority=True)
    # now we have the priority packet first in the TX queue
    assert (
        [x['seq'] for x in mote.tsch.txQueue] ==
        [2, 1]
    )

    # put another "normal" packet, which will be the last packet in
    # the TX queue
    normal_packet = copy.deepcopy(base_dummy_packet)
    normal_packet['seq'] = 3
    mote.tsch.enqueue(normal_packet, priority=False)
    assert (
        [x['seq'] for x in mote.tsch.txQueue] ==
        [2, 1, 3]
    )

    # lastly, put another "priority" packet, which should be the next
    # packet of the first priority packet
    priority_packet = copy.deepcopy(base_dummy_packet)
    priority_packet['seq'] = 4
    mote.tsch.enqueue(priority_packet, priority=True)
    # now we have the priority packet first in the TX queue
    assert (
        [x['seq'] for x in mote.tsch.txQueue] ==
        [2, 4, 1, 3]
    )

    for i in range(5, sim_engine.settings.tsch_tx_queue_size + 1):
        normal_packet = copy.deepcopy(base_dummy_packet)
        normal_packet['seq'] = i
        mote.tsch.enqueue(normal_packet, priority=False)

    # the TX queue should be full
    assert len(mote.tsch.txQueue) == sim_engine.settings.tsch_tx_queue_size

    # seq of the last packet should be the same as the TX queue size
    assert (
        mote.tsch.txQueue[-1]['seq'] ==
        sim_engine.settings.tsch_tx_queue_size
    )

    # add another priority packet
    priority_packet = copy.deepcopy(base_dummy_packet)
    new_pkt_seq = sim_engine.settings.tsch_tx_queue_size + 1
    priority_packet['seq'] = new_pkt_seq
    mote.tsch.enqueue(priority_packet, priority=True)

    # the first three packets should be priority
    assert (
        [x['seq'] for x in mote.tsch.txQueue[0:3]] ==
        [2, 4, new_pkt_seq]
    )
    # the TX queue length shouldn't exceed the queue size
    assert len(mote.tsch.txQueue) == sim_engine.settings.tsch_tx_queue_size
    # the last packet in the queue should have
    # (sim_engine.settings.tsch_tx_queue_size - 1) for its seq
    priority_packet['seq'] = sim_engine.settings.tsch_tx_queue_size

    # put the last normal packet in pktToSend, which should not be
    # dropped by enqueuing a priority packet
    normal_packet = mote.tsch.txQueue[-1]
    assert normal_packet['mac']['priority'] is False
    mote.tsch.pktToSend = normal_packet

    priority_packet = copy.deepcopy(base_dummy_packet)
    new_pkt_seq = sim_engine.settings.tsch_tx_queue_size + 1
    priority_packet['seq'] = new_pkt_seq
    mote.tsch.enqueue(priority_packet, priority=True)

    assert priority_packet in mote.tsch.txQueue
    assert normal_packet
    assert normal_packet in mote.tsch.txQueue

    mote.tsch.pktToSend = None

    # change all the packet in the TX queue to priority
    for packet in mote.tsch.txQueue:
        packet['mac']['priority'] = True

    # add a priority packet, which should be dropped
    priority_packet = copy.deepcopy(base_dummy_packet)
    last_pkt_seq = sim_engine.settings.tsch_tx_queue_size + 2
    priority_packet['seq'] = last_pkt_seq
    mote.tsch.enqueue(priority_packet, priority=True)
    assert len(mote.tsch.txQueue) == sim_engine.settings.tsch_tx_queue_size
    assert mote.tsch.txQueue[-1]['seq'] != last_pkt_seq

def test_removeTypeFromQueue(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1,
        },
    )

    mote = sim_engine.motes[0]

    mote.tsch.txQueue = [
        {'type': 1},
        {'type': 2},
        {'type': 3},
        {'type': 4},
        {'type': 3},
        {'type': 5},
    ]
    mote.tsch.remove_packets_in_tx_queue(type=3)
    assert mote.tsch.txQueue == [
        {'type': 1},
        {'type': 2},
        # removed
        {'type': 4},
        # removed
        {'type': 5},
    ]

@pytest.mark.parametrize('destination, packet_type, expected_cellOptions', [
    ('parent',    d.PKT_TYPE_DATA, [d.CELLOPTION_TX]),
])
def test_tx_cell_selection(
        sim_engine,
        packet_type,
        destination,
        expected_cellOptions
    ):

    # cell selection rules:
    #
    # - [CELLOPTION_TX] should be used for a unicast packet to a neighbor to whom a sender
    #   has a dedicated TX cell
    # - [CELLOPTION_TX,CELLOPTION_RX,CELLOPTION_SHARED] should be used otherwise
    #
    # With force_initial_routing_and_scheduling_state True, each mote has one
    # shared (TX/RX/SHARED) cell and one TX cell to its parent.

    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'            : 3,
            'sf_class'                  : 'SFNone',
            'conn_class'               : 'Linear',
            'app_pkPeriod'             : 0,
            'app_pkPeriodVar'          : 0,
            'tsch_probBcast_ebProb'    : 0,
        },
        force_initial_routing_and_scheduling_state = True
    )

    parent = sim_engine.motes[0]
    mote   = sim_engine.motes[1]
    child  = sim_engine.motes[2]

    packet = {
        'type':         packet_type,
        'app': {
            'rank':     mote.rpl.get_rank(),
        },
        'net': {
            'srcIp':    mote.get_ipv6_link_local_addr()
        },
    }

    # With packet_type=d.PKT_TYPE_DATA, we'll test if the right cell is chosen
    # to send a fragment. Set 180 to packet_length so that the packet is
    # divided into two fragments.
    if packet_type == d.PKT_TYPE_DATA:
        packet['net']['packet_length'] = 180

    # set destination IPv6 address and and a corresponding neighbor entry
    if   destination == 'broadcast':
        packet['net']['dstIp'] = d.IPV6_ALL_RPL_NODES_ADDRESS
    elif destination == 'parent':
        packet['net']['dstIp'] = parent.get_ipv6_link_local_addr()
        mote.sixlowpan.on_link_neighbor_list.append(parent.get_mac_addr())
    elif destination == 'child':
        packet['net']['dstIp'] = child.get_ipv6_link_local_addr()
        mote.sixlowpan.on_link_neighbor_list.append(child.get_mac_addr())

    # send a packet to the target destination
    mote.sixlowpan.sendPacket(packet)

    # wait for long enough for the packet to be sent
    u.run_until_asn(sim_engine, 1000)

    # see logs
    logs = []

    # as mentioned above, we'll see logs for fragment packets when
    # packet_type=d.PKT_TYPE_DATA
    if packet_type == d.PKT_TYPE_DATA:
        test_packet_type = d.PKT_TYPE_FRAG
    else:
        test_packet_type = packet_type

    for log in u.read_log_file(filter=['tsch.txdone']):
        if  (
                (mote.is_my_mac_addr(log['packet']['mac']['srcMac']))
                and
                (log['packet']['type']          == test_packet_type)
            ):
            logs.append(log)

    # transmission could be more than one due to retransmission
    assert(len(logs) > 0)

    for log in logs:
        slotframe = mote.tsch.slotframes[0]
        cell = slotframe.get_cells_at_asn(log['_asn'])[0]
        assert cell.options == expected_cellOptions

@pytest.fixture(params=[d.PKT_TYPE_EB, d.PKT_TYPE_DIO])
def fixture_adv_frame(request):
    return request.param

def test_network_advertisement(sim_engine, fixture_adv_frame):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes':                1,
            'exec_numSlotframesPerRun':     100, # with 101 slots per slotframe, that's 10,100 slot total
        }
    )

    u.run_until_asn(sim_engine, 10000)

    logs = u.read_log_file(filter=['tsch.txdone'])
    # root should send more than one EB in a default simulation run
    assert len([l for l in logs if l['packet']['type'] == fixture_adv_frame]) > 0


@pytest.fixture(params=['dedicated-cell', 'shared-cell'])
def cell_type(request):
    return request.param

def test_retransmission_count(sim_engine):
    max_tx_retries = 5
    sim_engine = sim_engine(
        diff_config = {
            'exec_numSlotframesPerRun': 10,
            'exec_numMotes'           : 2,
            'app_pkPeriod'            : 0,
            'rpl_daoPeriod'           : 0,
            'tsch_probBcast_ebProb'   : 0,
            'secjoin_enabled'         : False,
            'tsch_keep_alive_interval': 0,
            'tsch_max_tx_retries'     : max_tx_retries,
            'conn_class'              : 'Linear'
        },
        force_initial_routing_and_scheduling_state = True
    )

    # short-hands
    root = sim_engine.motes[0]
    hop1 = sim_engine.motes[1]
    connectivity_matrix = sim_engine.connectivity.matrix

    # stop DIO timer
    root.rpl.trickle_timer.stop()
    hop1.rpl.trickle_timer.stop()

    # set 0% of PDR to the link between the two motes
    for channel in d.TSCH_HOPPING_SEQUENCE:
        connectivity_matrix.set_pdr_both_directions(
            root.id,
            hop1.id,
            channel,
            0
        )

    # make hop1 send an application packet
    hop1.app._send_a_single_packet()

    # run the simulation
    u.run_until_end(sim_engine)

    # check the log
    tx_logs = u.read_log_file([SimLog.LOG_TSCH_TXDONE['type']])

    # hop1 should send out the frame six times: 1 for the initial transmission
    # and 5 for retransmissions
    assert len(tx_logs) == 1 + max_tx_retries
    for tx_log in tx_logs:
        assert tx_log['packet']['type'] == d.PKT_TYPE_DATA
        assert hop1.is_my_ipv6_addr(tx_log['packet']['net']['srcIp'])
        assert tx_log['packet']['app']['appcounter'] == 0

def test_retransmission_backoff_algorithm(sim_engine, cell_type):
    max_tx_retries = 100
    sim_engine = sim_engine(
        diff_config = {
            'exec_numSlotframesPerRun': 10000,
            'exec_numMotes'           : 2,
            'app_pkPeriod'            : 0,
            'secjoin_enabled'         : False,
            'tsch_keep_alive_interval': 0,
            'tsch_max_tx_retries'     : max_tx_retries
        }
    )
    sim_log = SimLog.SimLog()

    # filter logs to make this test faster; we need only SimLog.LOG_TSCH_TXDONE
    sim_log.set_log_filters([SimLog.LOG_TSCH_TXDONE['type']])

    # for quick access
    root  = sim_engine.motes[0]
    hop_1 = sim_engine.motes[1]
    slotframe_length = sim_engine.settings.tsch_slotframeLength

    #== test setup ==

    u.run_until_everyone_joined(sim_engine)

    # make hop_1 ready to send an application packet
    assert hop_1.rpl.dodagId is None
    dio = root.rpl._create_DIO()
    dio['mac'] = {'srcMac': root.get_mac_addr()}
    hop_1.rpl.action_receiveDIO(dio)
    assert hop_1.rpl.dodagId is not None

    # make root ignore all the incoming frame for this test
    def ignoreRx(self, packet, channel):
        self.waitingFor = None
        isACKed         = False
        return isACKed
    root.tsch.rxDone = types.MethodType(ignoreRx, root.tsch)

    if cell_type == 'dedicated-cell':
        # allocate one TX=1/RX=1/SHARED=1 cell to the motes as their dedicate cell.
        cellOptions   = [d.CELLOPTION_TX, d.CELLOPTION_RX, d.CELLOPTION_SHARED]

        assert len(root.tsch.get_cells(hop_1.get_mac_addr())) == 0
        root.tsch.addCell(1, 1, hop_1.get_mac_addr(), cellOptions)
        assert len(root.tsch.get_cells(hop_1.get_mac_addr())) == 1

        assert len(hop_1.tsch.get_cells(root.get_mac_addr())) == 0
        hop_1.tsch.addCell(1, 1, root.get_mac_addr(), cellOptions)
        assert len(hop_1.tsch.get_cells(root.get_mac_addr())) == 1

    # make sure hop_1 send a application packet when the simulator starts
    hop_1.tsch.txQueue = []
    hop_1.app._send_a_single_packet()
    assert len(hop_1.tsch.txQueue) == 1

    #== start test ==
    asn_starting_test = sim_engine.getAsn()
    # run the simulator until hop_1 drops the packet or the simulation ends
    def drop_packet(self, packet, reason):
        if packet['type'] == d.PKT_TYPE_DATA:
            # pause the simulator
            sim_engine.pauseAtAsn(sim_engine.getAsn() + 1)
    hop_1.drop_packet = types.MethodType(drop_packet, hop_1)
    u.run_until_end(sim_engine)

    # confirm
    # - hop_1 sent the application packet to the root
    # - retransmission backoff worked
    logs = u.read_log_file(
        filter     = [SimLog.LOG_TSCH_TXDONE['type']],
        after_asn  = asn_starting_test
    )
    app_data_tx_logs = []
    for log in logs:
        if (
                (log['_mote_id'] == hop_1.id)
                and
                (root.is_my_mac_addr(log['packet']['mac']['dstMac']))
                and
                (log['packet']['type'] == d.PKT_TYPE_DATA)
            ):
            app_data_tx_logs.append(log)

    assert len(app_data_tx_logs) == 1 + max_tx_retries

    # all transmission should have happened only on the dedicated cell if it's
    # available (it shouldn't transmit a unicast frame to the root on the
    # minimal (shared) cell.
    if   cell_type == 'dedicated-cell':
        _cell = hop_1.tsch.get_cells(root.get_mac_addr())[0]
        expected_cell_offset = _cell.slot_offset
    elif cell_type == 'shared-cell':
        expected_cell_offset = 0   # the minimal (shared) cell
    else:
        raise NotImplementedError()

    for log in app_data_tx_logs:
        slot_offset = log['_asn'] % slotframe_length
        assert slot_offset == expected_cell_offset

    # retransmission should be performed after backoff wait; we should see gaps
    # between consecutive retransmissions. If all the gaps are 101 slots, that
    # is, one slotframe, this means there was no backoff wait between
    # transmissions.
    timestamps = [log['_asn'] for log in app_data_tx_logs]
    diffs = [x[1] - x[0] for x in zip(timestamps[:-1], timestamps[1:])]
    assert len([diff for diff in diffs if diff != slotframe_length]) > 0

def test_eb_by_root(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )

    root = sim_engine.motes[0]
    eb = root.tsch._create_EB()

    # From Section 6.1 of RFC 8180:
    #   ...
    #   DAGRank(rank(0))-1 = 0 is compliant with 802.15.4's requirement of
    #   having the root use Join Metric = 0.
    assert eb['mac']['join_metric'] == 0

def test_select_active_tx_cell(sim_engine):
    # this test is for a particular case; it's not a general test for
    # Tsch._select_active_cell()

    max_tx_retries = 5
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'         : 3,
            'tsch_max_tx_retries': max_tx_retries
        }
    )
    mote = sim_engine.motes[0]
    neighbor_mac_addr_1 = sim_engine.motes[1].get_mac_addr()
    neighbor_mac_addr_2 = sim_engine.motes[2].get_mac_addr()
    txshared_cell_options = [d.CELLOPTION_TX, d.CELLOPTION_SHARED]

    # install one RX cell and one TX/SHARED cell. the TX/SHARED cell is
    # dedicated for the neighbor same slot offset
    mote.tsch.addCell(1, 1, neighbor_mac_addr_1, txshared_cell_options)
    mote.tsch.addCell(1, 1, neighbor_mac_addr_2, txshared_cell_options)

    # put one unicast frame for neighbor_1 to the TX queue first
    frame_1 = {
        'type': d.PKT_TYPE_DATA,
        'mac': {
            'dstMac': neighbor_mac_addr_1,
            'retriesLeft': max_tx_retries
        }
    }
    mote.tsch.txQueue.append(frame_1)

    # put two unicast frames for neighbor_2 to the TX queue; the first of
    # the two frames is under retransmission
    frame_2 = {
        'type': d.PKT_TYPE_DATA,
        'mac': {
            'dstMac': neighbor_mac_addr_2,
            'retriesLeft': max_tx_retries
        }
    }
    frame_3 = {
        'type': d.PKT_TYPE_DATA,
        'mac': {
            'dstMac': neighbor_mac_addr_2,
            'retriesLeft': max_tx_retries
        }
    }
    frame_2['mac']['retriesLeft'] -= 1
    mote.tsch.txQueue.append(frame_2)
    mote.tsch.txQueue.append(frame_3)

    # set 1 to backoff_remaining_delay of frame_2 so that the TSCH stack skips
    # the cell for neighbor_mac_adddr_2
    frame_2['backoff_remaining_delay'] = 1

    # Tsch._select_active_cell() should select the cell for neighbor_mac_addr_1
    # because the frame for neighbor_mac_addr_2 is under retransmission
    candidate_cells = mote.tsch.slotframes[0].get_cells_at_asn(1)
    cell, packet = mote.tsch._select_active_cell(candidate_cells)

    assert mote.tsch.txQueue == [frame_1, frame_2, frame_3]
    assert cell is not None
    assert cell.mac_addr == neighbor_mac_addr_1
    assert packet == frame_1

def test_get_available_slots(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'       : 1,
            'tsch_slotframeLength': 101
        }
    )
    mote = sim_engine.motes[0]

    # by default, the mote has the minimal cell. So, its available cells are
    # slot offset 1 to 100.
    assert mote.tsch.get_available_slots() == list(range(1,101))

    # add one cell at slot offset 1
    mote.tsch.addCell(1, 1, None, [], 0)

    # slot offset 1 should not be in the available cells, now
    assert 1 not in mote.tsch.get_available_slots()

def test_get_physical_channel(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'       : 1,
            'tsch_slotframeLength': 101
        }
    )
    mote = sim_engine.motes[0]
    minimal_cell = mote.tsch.get_cell(
        slot_offset      = 0,
        channel_offset   = 0,
        mac_addr         = None,
        slotframe_handle = 0
    )

    assert minimal_cell is not None

    for i in range(len(d.TSCH_HOPPING_SEQUENCE)):
        if i > 0:
            u.run_until_asn(
                sim_engine,
                (
                    sim_engine.getAsn() +
                    sim_engine.settings.tsch_slotframeLength
                )
            )
            assert (
                previous_channel !=
                mote.tsch._get_physical_channel(minimal_cell)
            )
        else:
            pass
        previous_channel = mote.tsch._get_physical_channel(minimal_cell)


@pytest.fixture(params=[False, True])
def fixture_pending_bit_enabled(request):
    return request.param

def test_pending_bit(sim_engine, fixture_pending_bit_enabled):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'           : 2,
            'exec_numSlotframesPerRun': 3,
            'sf_class'                : 'SFNone',
            'secjoin_enabled'         : False,
            'app_pkPeriod'            : 0,
            'rpl_daoPeriod'           : 0,
            'tsch_keep_alive_interval': 0,
            'conn_class'              : 'Linear'
        }
    )

    # short-hands
    root = sim_engine.motes[0]
    mote = sim_engine.motes[1]

    # get the mote joined the network
    eb = root.tsch._create_EB()
    eb_dummy = {
        'type':            d.PKT_TYPE_EB,
        'mac': {
            'srcMac':      '00-00-00-AA-AA-AA',     # dummy
            'dstMac':      d.BROADCAST_ADDRESS,     # broadcast
            'join_metric': 1000
        }
    }
    mote.tsch._action_receiveEB(eb)
    mote.tsch._action_receiveEB(eb_dummy)
    dio = root.rpl._create_DIO()
    dio['mac'] = {'srcMac': root.get_mac_addr()}
    mote.rpl.action_receiveDIO(dio)

    # activate the pending bit feature if necessary
    if fixture_pending_bit_enabled:
        root.tsch.enable_pending_bit()
        mote.tsch.enable_pending_bit()

    # add a shared cell on slot_offset 1 and channel offset 1
    root.tsch.addCell(1, 1, None, [d.CELLOPTION_RX])
    mote.tsch.addCell(
        1,
        1,
        root.get_mac_addr(),
        [
            d.CELLOPTION_TX, d.CELLOPTION_SHARED
        ]
    )

    # put two DATA packets and one DIO between them to the TX queue of the mote
    mote.tsch.txQueue = []
    assert len(mote.tsch.txQueue) == 0
    mote.app._send_packet(
        dstIp         = root.get_ipv6_global_addr(),
        packet_length = 10
    )
    mote.rpl._send_DIO()
    mote.app._send_packet(
        dstIp         = root.get_ipv6_global_addr(),
        packet_length = 10
    )
    assert len(mote.tsch.txQueue) == 3

    u.run_until_end(sim_engine)

    # check logs
    logs = [
        log
        for log in u.read_log_file(filter=[SimLog.LOG_TSCH_TXDONE['type']])
        if log['packet']['type'] == d.PKT_TYPE_DATA
    ]
    assert len(logs) == 2

    if fixture_pending_bit_enabled:
        # the second DATA packet is sent on the same channel as the first one
        # by the pending bit feature
        assert logs[0]['slot_offset'] == 1
        assert logs[0]['channel_offset'] == 1
        assert logs[1]['slot_offset'] == None
        assert logs[1]['channel_offset'] == None
        assert logs[0]['channel'] == logs[1]['channel']
        assert logs[1]['_asn'] - logs[0]['_asn'] == 1
    else:
        # two DATA packets should be sent on the shared cell in different slot
        # frames
        assert logs[0]['slot_offset'] == 1
        assert logs[0]['channel_offset'] == 1
        assert logs[1]['slot_offset'] == 1
        assert logs[1]['channel_offset'] == 1
        assert logs[0]['channel'] != logs[1]['channel']
        assert (
            (logs[1]['_asn'] - logs[0]['_asn']) ==
            sim_engine.settings.tsch_slotframeLength
        )

@pytest.fixture(params=[
    'no_diff',
    'slot_offset',
    'channel_offset',
    'cell_options',
    'mac_addr',
    'link_type'
])
def fixture_cell_comparison_test_type(request):
    return request.param

def test_cell_comparison(fixture_cell_comparison_test_type):
    cell_attributes = {
        'slot_offset'   : 1,
        'channel_offset': 2,
        'options'       : [d.CELLOPTION_TX],
        'mac_addr'      : None,
        'link_type'     : d.LINKTYPE_NORMAL
    }
    cell_1 = tsch.Cell(**cell_attributes)

    if fixture_cell_comparison_test_type == 'no_diff':
        # do nothing
        pass
    elif fixture_cell_comparison_test_type == 'slot_offset':
        cell_attributes['slot_offset'] += 1
    elif fixture_cell_comparison_test_type == 'channel_offset':
        cell_attributes['channel_offset'] += 1
    elif fixture_cell_comparison_test_type == 'cell_options':
        cell_attributes['options'] = [d.CELLOPTION_RX]
    elif fixture_cell_comparison_test_type == 'mac_addr':
        cell_attributes['mac_addr'] = 'dummy_mac_addr'
    elif fixture_cell_comparison_test_type == 'link_type':
        cell_attributes['link_type'] = d.LINKTYPE_ADVERTISING
    else:
        raise NotImplementedError()

    cell_2 = tsch.Cell(**cell_attributes)

    if fixture_cell_comparison_test_type == 'no_diff':
        assert cell_1 == cell_2
    else:
        assert cell_1 != cell_2

def test_advertising_link(sim_engine):
    # EB should be sent only on links having ADVERTISING on
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1,
            'sf_class'     : 'SFNone',
            'tsch_slotframeLength' : 2,
            'tsch_probBcast_ebProb': 1.0,
        }
    )
    root = sim_engine.motes[0]
    # disable DIO so that there will be no traffic except for EBs.
    root.rpl.trickle_timer.stop()

    slotframe = root.tsch.get_slotframe(0)

    # make sure we have one cell
    assert len(slotframe.get_busy_slots()) == 1
    cells = slotframe.get_cells_by_mac_addr(None)
    assert len(cells) == 1

    # the link-type of the minimal cell should be ADVERTISING
    minimal_cell = cells[0]
    assert minimal_cell.slot_offset == 0
    assert minimal_cell.channel_offset == 0
    assert (
        sorted(minimal_cell.options) ==
        sorted([
            d.CELLOPTION_RX,
            d.CELLOPTION_TX,
            d.CELLOPTION_SHARED
        ])
    )
    assert minimal_cell.mac_addr == None
    assert minimal_cell.link_type == d.LINKTYPE_ADVERTISING

    # add one cell whose link-type is NORMAL at slotoffset 1
    normal_cell = tsch.Cell(
        slot_offset    = 1,
        channel_offset = 1,
        options        = minimal_cell.options,
        mac_addr       = None,
        link_type      = d.LINKTYPE_NORMAL
    )
    assert normal_cell.link_type == d.LINKTYPE_NORMAL
    slotframe.add(normal_cell)

    # run the simulation; we should have EBs only on the minimal cells
    u.run_until_end(sim_engine)

    tx_logs = u.read_log_file(filter=[SimLog.LOG_TSCH_TXDONE['type']])
    assert len(tx_logs) > 0
    for tx_log in tx_logs:
        assert tx_log['slot_offset'] != normal_cell.slot_offset

def test_get_cells(sim_engine):
    SLOTFRAME_LENGTH = 101
    sim_engine = sim_engine(
        diff_config=
        {
            'exec_numMotes'       : 1,
            'tsch_slotframeLength': SLOTFRAME_LENGTH
        }
    )
    mote = sim_engine.motes[0]

    assert len(mote.tsch.get_cells()) == 1

    # add slotframe 1
    mote.tsch.add_slotframe(1, SLOTFRAME_LENGTH)
    # add a cell having None for its mac_addr
    mote.tsch.addCell(
        slotOffset    = 1,
        channelOffset = 1,
        neighbor      = None,
        cellOptions   = [
            d.CELLOPTION_TX,
            d.CELLOPTION_RX,
            d.CELLOPTION_SHARED
        ],
        slotframe_handle = 1
    )

    # get_cells() should return 2 now
    assert len(mote.tsch.get_cells()) == 2

@pytest.fixture(params=['root', 'mote_1'])
def fixture_clock_source(request):
    return request.param

def test_eb_wait_timer(sim_engine, fixture_clock_source):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'        : 3,
            'secjoin_enabled'      : False,
            'tsch_probBcast_ebProb': 0
        }
    )

    assert d.TSCH_MAX_EB_DELAY == 180
    assert d.TSCH_NUM_NEIGHBORS_TO_WAIT == 2

    root = sim_engine.motes[0]
    mote_1 = sim_engine.motes[1]
    mote_2 = sim_engine.motes[2]

    # give an EB to mote_1, which will get synchronized after 180
    # seconds
    eb_root = root.tsch._create_EB()
    mote_1.tsch._action_receiveEB(eb_root)

    # run the simulation for 180 seconds - 1 slot
    u.run_until_asn(
        sim_engine,
        (
            sim_engine.getAsn() +
            old_div(d.TSCH_MAX_EB_DELAY, sim_engine.settings.tsch_slotDuration) - 1
        )
    )
    assert mote_1.tsch.isSync is False
    # proceed one slot
    u.run_until_asn(sim_engine, sim_engine.getAsn() + 1)
    assert mote_1.tsch.isSync is True
    # the EB list should be empty
    assert not mote_1.tsch.received_eb_list

    # give a DIO to mote_1 so that mote_1 can create an EB
    dio = root.rpl._create_DIO()
    dio['mac'] = {'srcMac': root.get_mac_addr()}
    mote_1.rpl.action_receiveDIO(dio)
    eb_mote_1 = mote_1.tsch._create_EB()

    # ajudst join metric
    if fixture_clock_source == 'root':
        eb_root['mac']['join_metric'] = 1
        eb_mote_1['mac']['join_metric'] = 100
    elif fixture_clock_source == 'mote_1':
        eb_root['mac']['join_metric'] = 100
        eb_mote_1['mac']['join_metric'] = 1
    else:
        raise NotImplementedError(fixture_clock_source)

    # give the EB to mote_2
    mote_2.tsch._action_receiveEB(eb_root)
    assert mote_2.tsch.isSync is False

    # give an EB of mote_1 to mote_2, which makes mote_2 get
    # synchronized immediately
    mote_2.tsch._action_receiveEB(eb_mote_1)
    assert mote_2.tsch.isSync is True
    # the EB list should be empty
    assert not mote_2.tsch.received_eb_list

    # mote_2 should select one as fixture_clock_source
    if fixture_clock_source == 'root':
        assert mote_2.tsch.clock.source == root.get_mac_addr()
    else:
        assert mote_2.tsch.clock.source == mote_1.get_mac_addr()

@pytest.fixture(params=[True, False])
def fixture_frame_from_root(request):
    return request.param

@pytest.fixture(params=[-1, 10])
def fixture_keep_alive_interval(request):
    return request.param

def test_desync(
        sim_engine,
        fixture_frame_from_root,
        fixture_keep_alive_interval
):
    tsch_slotDuration = 0.01
    tsch_slotframeLength = 101
    exec_numSlotframesPerRun = 1000
    if fixture_keep_alive_interval < 0:
        # no keep-alive message, but synchronization timer is active
        fixture_keep_alive_interval = (
            tsch_slotDuration *
            tsch_slotframeLength *
            (exec_numSlotframesPerRun + 1)
        )

    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'           : 2,
            'exec_numSlotframesPerRun': exec_numSlotframesPerRun,
            'tsch_keep_alive_interval': fixture_keep_alive_interval,
            'app_pkPeriod'            : 0,
            'tsch_probBcast_ebProb'   : 0,
            'tsch_slotDuration'       : tsch_slotDuration,
            'tsch_slotframeLength'     : tsch_slotframeLength,
            'secjoin_enabled'         : False,
            'rpl_extensions'          : []
        }
    )

    root = sim_engine.motes[0]
    mote = sim_engine.motes[1]

    # disable DIO transmission
    root.rpl.trickle_timer.stop()

    # get mote synchronized
    eb = root.tsch._create_EB()
    mote.tsch._action_receiveEB(eb)
    mote.engine.removeFutureEvent((mote.id, 'tsch', 'wait_eb'))
    mote.tsch._perform_synchronization()
    assert mote.tsch.isSync

    if fixture_frame_from_root:
        def _decided_to_send_eb(self):
            return True
        root.tsch._decided_to_send_eb = types.MethodType(
            _decided_to_send_eb,
            root.tsch
        )
    else:
        # do nothing; root won't send any packet
        pass

    # run until the end
    u.run_until_end(sim_engine)

    logs = u.read_log_file(filter=['tsch.desynced'])
    if fixture_frame_from_root or (fixture_keep_alive_interval == 10):
        # if mote receives something from the root, either a frame or
        # an ACK to a keep-alive frame, it can keep synchronized
        assert len(logs) == 0
    else:
        assert len(logs) == 1
        log = logs[0]
        assert log['_mote_id'] == mote.id
        assert log['_asn'] == d.TSCH_DESYNCHRONIZED_TIMEOUT_SLOTS

def test_tx_queue_of_infinite_size(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes'     : 1,
            'tsch_tx_queue_size': -1
        }
    )
    mote = sim_engine.motes[0]

    # put 100 packets to tx queue
    num_packets = 100
    for _ in range(num_packets):
        packet = {
            'type': d.PKT_TYPE_DATA,
            'mac' : {
                'srcMac': mote.get_mac_addr(),
                'dstMac': mote.get_mac_addr()
            }
        }
        mote.tsch.enqueue(packet)

    assert len(mote.tsch.txQueue) == num_packets
