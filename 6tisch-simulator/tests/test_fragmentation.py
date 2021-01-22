"""
Tests for 6LoWPAN fragmentation
"""
from __future__ import absolute_import
from __future__ import division

from builtins import zip
from builtins import range
from past.utils import old_div
from builtins import object
import copy
import math

import pytest

from . import test_utils as u
import SimEngine
import SimEngine.Mote.MoteDefines as d

# =========================== helpers =========================================

def get_memory_usage(mote, fragmentation):
    if fragmentation == 'PerHopReassembly':
        memory_structure = mote.sixlowpan.fragmentation.reassembly_buffers
    elif fragmentation == 'FragmentForwarding':
        memory_structure = mote.sixlowpan.fragmentation.vrb_table

    return sum([len(e) for _, e in list(memory_structure.items())])

# =========================== fixtures ========================================

FRAGMENTATION = [
    'PerHopReassembly',
    'FragmentForwarding'
]
@pytest.fixture(params=FRAGMENTATION)
def fragmentation(request):
    return request.param

FRAGMENTATION_FF_DISCARD_VRB_ENTRY_POLICY = [
    [],
    ['last_fragment'],
    ['missing_fragment'],
    ['last_fragment', 'missing_fragment']
]
@pytest.fixture(params=FRAGMENTATION_FF_DISCARD_VRB_ENTRY_POLICY)
def fragmentation_ff_discard_vrb_entry_policy(request):
    return request.param

# =========================== tests ===========================================

class TestFreeRun(object):
    @pytest.fixture(params=[0, 1])
    def sixlowpan_reassembly_buffers_num(self, request):
        return request.param

    @pytest.fixture(params=[0, 50])
    def fragmentation_ff_vrb_table_size(self, request):
        return request.param

    def test_with_no_memory_for_fragment(
            self,
            sim_engine,
            sixlowpan_reassembly_buffers_num,
            fragmentation_ff_vrb_table_size,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy
        ):

        # We allocate no memory for PerHopReassembly and for FragmentForwarding
        # in order to see the stack behavior under the situation where it
        # cannot add an reassembly buffer nor VRB Table entry for an incoming
        # fragment.

        if (
                (sixlowpan_reassembly_buffers_num > 0)
                and
                (fragmentation_ff_vrb_table_size > 0)
            ):
            # we skip this combination of parameters
            return

        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes'                            : 3,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'app_pkPeriod'                             : 5,
                'app_pkPeriodVar'                          : 0,
                'tsch_probBcast_ebProb'                    : 0,
                'sixlowpan_reassembly_buffers_num'         : sixlowpan_reassembly_buffers_num,
                'fragmentation_ff_vrb_table_size'          : fragmentation_ff_vrb_table_size,
                'app_pkLength'                             : 180,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True,
            )

        u.run_until_asn(sim_engine, 5000)

        # send an application packet from root to the other motes for test with
        # downward traffic
        sim_engine.motes[0].app._send_ack(sim_engine.motes[1].id, 180)
        sim_engine.motes[0].app._send_ack(sim_engine.motes[2].id, 180)

        u.run_until_asn(sim_engine, 10100)

class TestPacketDelivery(object):
    """ Behavioral Testing for Fragmentation
    """

    APP_PKLENGTH = [45, 90, 135, 180]
    @pytest.fixture(params=APP_PKLENGTH)
    def app_pkLength(self, request):
        return request.param

    def test_no_fragment_loss(
            self,
            sim_engine,
            app_pkLength,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy
        ):
        """ Test it with a basic case in which there is no fragment loss
        - objective   : test if packets are delivered to the root (destination)
        - precondition: form a 3-mote linear topology
        - action      : send packets from each motes except for the root
        - expectation : the root receives the packets
        """

        sim_engine = sim_engine(
            {
                'exec_numMotes'                            : 3,
                'exec_numSlotframesPerRun'                 : 10000,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'app_pkPeriod'                             : 5,
                'app_pkPeriodVar'                          : 0,
                'tsch_probBcast_ebProb'                    : 0,
                'sixlowpan_reassembly_buffers_num'         : 2,
                'app_pkLength'                             : app_pkLength,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True,
        )

        # run the simulation for 1000 timeslots (10 seconds)
        u.run_until_asn(sim_engine, 1000)

        # the root should receive packet from both of the two motes during 10 seconds.
        # - Packets are generated at every 5 seconds
        # - The first packet is generated within the first 5 seconds
        # - the minimum e2e latency of one fragment from the leaf is about 2 sec
        # - a packet is divided into two fragments at most in this test
        # - two fragments from the leaf need at least 4 sec to reach the root
        senders = []
        for log in u.read_log_file(filter=['app.rx']):
            srcIp = log['packet']['net']['srcIp']
            if srcIp not in senders:
                senders.append(srcIp)
            if len(senders) == 2:
                # root should receive packets from both of the two motes
                # if it reaches here, it means success
                return

        assert False

    TARGET_DATAGRAM_OFFSET = [0, 90, 180]
    @pytest.fixture(params=TARGET_DATAGRAM_OFFSET)
    def target_datagram_offset(self, request):
        return request.param

    def test_fragment_loss(
            self,
            sim_engine,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy,
            target_datagram_offset,
        ):
        """ Test fragmentation with fragment loss
        - objective   : test if a packet is lost there is a missing fragment
        - precondition: form a 3-mote linear topology
        - precondition: app scheduled is done by hand (app_pkPeriod=0)
        - precondition: a packet is divided into three fragments
        - action      : send a packet from the leaf
        - action      : drop one fragment of the packet
        - expectation : the root doesn't receive (reassemble) the packet
        """
        sim_engine = sim_engine(
            {
                'exec_numMotes'                            : 3,
                'exec_numSlotframesPerRun'                 : 10,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'app'                                      : 'AppPeriodic',
                'app_pkPeriod'                             : 0,
                'app_pkPeriodVar'                          : 0,
                'app_pkLength'                             : 270,
                'tsch_probBcast_ebProb'                    : 0,
                'sixlowpan_reassembly_buffers_num'         : 2,
                'tsch_max_payload_len'                     : 90,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True
        )

        # send a packet from the leaf mote
        leaf = sim_engine.motes[2]
        # _send_a_single_packet() causes leaf to send a packet
        leaf.app._send_a_single_packet()

        # retrieve fragments in its TX queue
        fragments = []
        for frame in leaf.tsch.txQueue:
            if frame['type'] == d.PKT_TYPE_FRAG:
                fragments.append(frame)

        # make sure its TX queue has three fragments
        assert len(fragments) == 3

        # remove one fragment from the TX queue
        for fragment in fragments:
            if fragment['net']['datagram_offset'] == target_datagram_offset:
                leaf.tsch.txQueue.remove(fragment)
                break

        # it's ready to test; run the simulation for long enough time
        u.run_until_asn(sim_engine, 1000)

        # the root should not receive a packet from the leaf
        # - the intermediate node should receive two fragments
        # - the number of fragment receptions by the root depends:
        #   - if the 1st fragment is lost, the root receives one fragment
        #   - if the 2nd or 3rd fragment is lost, the root receives two
        # - the root should not be able to reassemble a packet
        # - the root should not receive the packet
        logs = u.read_log_file(
            filter=[
                'app.rx',
                'sixlowpan.pkt.rx'
            ]
        )

        fragment_reception_count = 0
        for log in logs:
            if (
                    (log['_type']          == 'sixlowpan.pkt.rx')
                    and
                    (log['_mote_id']       == 1)
                    and
                    (log['packet']['type'] == d.PKT_TYPE_FRAG)
               ):
                # count the fragment receptions by the intermediate node, whose
                # _mote_id is 1
                fragment_reception_count += 1
            elif log['_type'] == 'app.rx':
                # this should never happen; a packet never reaches the root
                assert False

        # again, the intermediate node should receive two fragments from the
        # leaf
        assert fragment_reception_count == 2

    def test_out_of_order_frame(self):
        """Test fragmentation with out-of-order fragments
        """
        # We don't need tests on out-of-order fragments since it doesn't happen
        # with this simulator. Even in reality, it rarely happens.
        pass

    def test_e2e_latency(
            self,
            sim_engine,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy,
        ):
        """Test end-to-end latency of a fragmented packet
        - objective   : test if each forwarding technique shows expected end-to-end latency
        - precondition: form a 4-mote linear topology
        - precondition: a packet is divided into two fragments
        - action      : send a packet from the leaf to the root
        - expectation : the root should receive the last fragment in slotframes of the
                        expected number after the first one is tran
        - note        : the intermediate node has a RX cell to the root just *after*
                        a TX cell from the leaf
        """

        # latency is expressed in the number of slotframes
        expected_e2e_latency = {
            'PerHopReassembly'  : 6,
            'FragmentForwarding': 4
        }

        sim_engine = sim_engine(
            {
                'exec_numMotes'                            : 4,
                'exec_numSlotframesPerRun'                 : 10,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'rpl_daoPeriod'                            : 0,
                'app_pkPeriod'                             : 0,
                'app_pkPeriodVar'                          : 0,
                'tsch_probBcast_ebProb'                    : 0,
                'app_pkLength'                             : 180,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True
        )
        sim_settings = SimEngine.SimSettings.SimSettings()

        # send a packet; its fragments start being forwarded at the next
        # timeslot where it has a dedicated TX cell
        leaf = sim_engine.motes[3]
        # _send_a_single_packet() causes leaf to send a packet
        leaf.app._send_a_single_packet()

        # run the simulation for long enough time
        u.run_until_asn(sim_engine, 1000)

        logs = u.read_log_file(
            filter=[
                'app.rx',
                'prop.transmission'
            ]
        )

        # asn_start: ASN the first fragment is transmitted by the leaf
        # asn_end  : ASN the last fragment is received by the root
        asn_start  = 0
        asn_end = 0

        for log in logs:
            if  (
                    (log['_type'] == 'sixlowpan.pkt.tx') and
                    (log['packet']['srcMac'] == 3) and
                    (log['packet']['type'] == d.PKT_TYPE_FRAG)
                ):
                asn_start = log['_asn']

            if log['_type'] == 'app.rx':
                # log 'app.rx' means the last fragment is received
                # by the root
                asn_end = log['_asn']
                break

        e2e_latency = int(math.ceil(float(asn_end - asn_start) / sim_settings.tsch_slotframeLength))
        assert e2e_latency == expected_e2e_latency[fragmentation]

class TestFragmentationAndReassembly(object):

    TSCH_MAX_PAYLOAD    = 90
    TSCH_TX_QUEUE_SIZE  = 10
    MAX_APP_PAYLOAD_LEN = TSCH_MAX_PAYLOAD  * TSCH_TX_QUEUE_SIZE

    APP_PKLENGTH = list(range(TSCH_MAX_PAYLOAD+1, MAX_APP_PAYLOAD_LEN, TSCH_MAX_PAYLOAD))
    @pytest.fixture(params=APP_PKLENGTH)
    def app_pkLength(self, request):
        return request.param

    def test_fragmentation_and_reassembly(
            self,
            sim_engine,
            app_pkLength,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy
        ):
        """Test fragmentation and reassembly themselves (w/o forwarding)
        - objective   : test if a packet is divided to the expected number
        - precondition: form a 2-mote linear topology
        - precondition: app scheduled is done by hand (app_pkPeriod=0)
        - action      : send a packet to the root
        - expectation : the number of fragments is the expected value
        """
        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes'                            : 2,
                'exec_numSlotframesPerRun'                 : 20,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'app_pkPeriod'                             : 0,
                'app_pkPeriodVar'                          : 0,
                'tsch_probBcast_ebProb'                    : 0,
                'tsch_max_payload_len'                     : self.TSCH_MAX_PAYLOAD,
                'tsch_tx_queue_size'                       : self.TSCH_TX_QUEUE_SIZE,
                'app_pkLength'                             : app_pkLength,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True
        )

        # send a packet from the leaf mote
        leaf = sim_engine.motes[1]
        # _send_a_single_packet() causes leaf to send a packet
        leaf.app._send_a_single_packet()

        # it's ready to test; run the simulation for long enough time
        u.run_until_asn(sim_engine, 1500)

        # check if fragment receptions happen the expected times
        logs = u.read_log_file(filter=['sixlowpan.pkt.rx'])
        assert (
            len([log for log in logs if log['packet']['type'] == d.PKT_TYPE_FRAG]) ==
            math.ceil(float(app_pkLength) / self.TSCH_MAX_PAYLOAD)
        )

class TestMemoryManagement(object):
    """Test memory management for reassembly buffer and VRB table
    """

    MEMORY_LIMIT = list(range(1, 10, 1))
    @pytest.fixture(params=MEMORY_LIMIT)
    def memory_limit(self, request):
        return request.param
    def test_memory_limit(
            self,
            sim_engine,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy,
            memory_limit
        ):
        """Test memory limitation on reassembly buffer or VRB table
        - objective   : check if memory usage limitation works
        - precondition: form a 3-mote linear topology
        - action      : inject 10 fragments to hop1 mote
        - expectation : the number of reassembly buffer entries or
                        VRB table entries is the same as a specified
                        memory limitation value
        """

        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes'                   : 3,
                'fragmentation'                   : fragmentation,
                'fragmentation_ff_vrb_table_size' : memory_limit,
                'sixlowpan_reassembly_buffers_num': memory_limit
            },
            force_initial_routing_and_scheduling_state = True
        )

        root = sim_engine.motes[0]
        hop1 = sim_engine.motes[1]
        hop2 = sim_engine.motes[2]

        # inject 10 fragments to hop1; some of them should be dropped according
        # to memory_limit value in use
        for datagram_tag in range(0, 10):
            # root node has no limitation on memory size; test with a non-root
            # mote
            hop1.sixlowpan.recvPacket(
                {
                    'type': d.PKT_TYPE_FRAG,
                    'mac': {
                        'srcMac'               : hop2.id,
                        'dstMac'               : hop1.id
                    },
                    'net': {
                        'srcIp'                : hop2.id,
                        'dstIp'                : root.id,
                        'hop_limit'            : d.IPV6_DEFAULT_HOP_LIMIT,
                        'packet_length'        : 90,
                        'datagram_size'        : 180,
                        'datagram_tag'         : datagram_tag,
                        'datagram_offset'      : 0,
                    }
                }
            )

        # the memory usage should be the same as memory_limit
        assert get_memory_usage(hop1, fragmentation) == memory_limit

    def test_entry_expiration(
            self,
            sim_engine,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy
        ):
        """Test lifetime management on memory entries
        - objective   : test if an expired memory entry is removed
        - precondition: form a 3-mote linear topology
        - action      : inject a fragment to hop1 mote
        - action      : wait until 50% of its expiration time
        - action      : inject another fragment to hop1 mote
        - action      : wait until expiration time of the first created entry
        - action      : inject a fragment to hop1 mote to trigger memory housekeeping
        - expectation : the entry for the first fragment is removed
        """

        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes'                            : 3,
                'exec_numSlotframesPerRun'                 : 60,
                'app_pkPeriod'                             : 0,
                'app_pkPeriodVar'                          : 0,
                'tsch_probBcast_ebProb'                    : 0,
                'sixlowpan_reassembly_buffers_num'         : 2,
                'fragmentation_ff_vrb_table_size'          : 2,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy,
            },
            force_initial_routing_and_scheduling_state = True
        )
        sim_settings = SimEngine.SimSettings.SimSettings()

        root = sim_engine.motes[0]
        hop1 = sim_engine.motes[1]
        hop2 = sim_engine.motes[2]

        # prepare three fragments:
        # fragment1_0: the first fragment of a packet
        # fragment2_0: the first fragment of a different packet
        # fragment2_1: the second fragment of the different packet
        fragment1_0 = {
            'type':                d.PKT_TYPE_FRAG,
            'mac': {
                'srcMac':          hop2.id,
                'dstMac':          hop1.id,
            },
            'net': {
                'srcIp':           hop2.id,
                'dstIp':           root.id,
                'hop_limit':       d.IPV6_DEFAULT_HOP_LIMIT,
                'datagram_size'  : 270,
                'datagram_tag'   : 1,
                'datagram_offset': 0,
                'packet_length':   90
            }
        }
        fragment2_0                                = copy.copy(fragment1_0)
        fragment2_0['net']                         = copy.deepcopy(fragment1_0['net'])
        fragment2_0['net']['datagram_tag']         = 2
        fragment2_1                                = copy.copy(fragment2_0)
        fragment2_1['net']                         = copy.deepcopy(fragment2_0['net'])
        fragment2_1['net']['datagram_offset']      = 90
        fragment2_1['net']['original_packet_type'] = d.PKT_TYPE_DATA,

        # compute the lifetime of an entry
        slots_per_sec = int(1.0 / sim_settings.tsch_slotDuration)
        if fragmentation == 'PerHopReassembly':
            memory_lifetime = d.SIXLOWPAN_REASSEMBLY_BUFFER_LIFETIME * slots_per_sec
        elif fragmentation == 'FragmentForwarding':
            memory_lifetime = d.SIXLOWPAN_VRB_TABLE_ENTRY_LIFETIME * slots_per_sec
        expiration_time = memory_lifetime + 1

        # inject the first fragment
        assert get_memory_usage(hop1, fragmentation) == 0
        hop1.sixlowpan.recvPacket(fragment1_0)
        assert get_memory_usage(hop1, fragmentation) == 1

        # run the simulation until 50% of the lifetime
        u.run_until_asn(sim_engine, old_div(expiration_time, 2))

        # inject another fragment (the first fragment of a packet). hop1
        # creates a new entry for this fragment (packet)
        hop1.sixlowpan.recvPacket(fragment2_0)
        assert get_memory_usage(hop1, fragmentation) == 2

        # run the simulation until its expiration
        u.run_until_asn(sim_engine, expiration_time)

        # inject the other fragment (the second fragment of a packet). this
        # fragment doesn't cause hop1 to create a new entry
        hop1.sixlowpan.recvPacket(fragment2_1)

        # the memory should have only one entry for fragment2_0 and fragment2_1
        assert get_memory_usage(hop1, fragmentation) == 1

class TestDatagramTagManagement(object):
    """Test datagram_tag management
    """

    def test_datagram_tag_of_sending_packets(
            self,
            sim_engine,
            fragmentation,
            fragmentation_ff_discard_vrb_entry_policy
        ):
        """Test datagram_tag is incremented by one at packet source
        - objective    : test if fragment has correct datagram_tag
        - precondition : form a 3-mote linear topology
        - preconditono : a packet is divided into two fragments
        - action       : generate 5 packets at leaf node (10 fragments in total)
        - action       : inject all the fragment to hop1 node
        - expectation  : datagram_tag is incremented by one
        - expectation  : hop1 node decide a local unique datagram_tag for outgoing tag
        """

        sim_engine = sim_engine(
            {
                'exec_numMotes'                            : 3,
                'sf_class'                                 : 'SFNone',
                'conn_class'                               : 'Linear',
                'app_pkLength'                             : 180,
                'fragmentation'                            : fragmentation,
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy
            },
            force_initial_routing_and_scheduling_state = True
        )

        hop1 = sim_engine.motes[1]
        leaf = sim_engine.motes[2]

        # set initial datagram_tag for test purpose
        hop1_initial_next_datagram_tag = 10
        hop1.sixlowpan.fragmentation.next_datagram_tag = hop1_initial_next_datagram_tag

        leaf_initial_next_datagram_tag = 200
        leaf.sixlowpan.fragmentation.next_datagram_tag = leaf_initial_next_datagram_tag

        # generate five packets, each of them is divided into two fragments
        assert len(leaf.tsch.txQueue) == 0
        for _ in range(0, 5):
            # _send_a_single_packet() causes leaf to send a packet
            leaf.app._send_a_single_packet()
        assert len(leaf.tsch.txQueue) == 10

        # retrieve the fragments and see if datagram_tag is incremented by one
        expected_datagram_tag = leaf_initial_next_datagram_tag
        fragments_by_leaf = []
        for fragment in leaf.tsch.txQueue:
            assert fragment['type'] == d.PKT_TYPE_FRAG
            fragments_by_leaf.append(fragment)

            # test datagram_tag
            assert fragment['net']['datagram_tag'] == expected_datagram_tag

            # this is the last fragment; increment expected_datagram_tag
            if fragment['net']['datagram_offset'] == 90:
                expected_datagram_tag += 1

        # inject the fragments to hop1
        assert len(hop1.tsch.txQueue) == 0
        for i in range(0, len(fragments_by_leaf)):
            # inject a copied fragment to hop1
            fragment = copy.copy(fragments_by_leaf[i])
            fragment['net'] = copy.deepcopy(fragments_by_leaf[i]['net'])
            hop1.sixlowpan.recvPacket(fragment)

        # check outgoing datagram_tag is incremented by one
        expected_datagram_tag = hop1_initial_next_datagram_tag
        for fragment in hop1.tsch.txQueue:
            # test datagram_tag
            # datagram_tag should be updated by hop1
            assert fragment['net']['datagram_tag'] == expected_datagram_tag

            # this is the last fragment; increment expected_datagram_tag
            if fragment['net']['datagram_offset'] == 90:
                expected_datagram_tag += 1

        # incoming datagram_tag and outgoing datagram_tag should be different
        for (incoming_fragment, outgoing_fragment) in zip(fragments_by_leaf, hop1.tsch.txQueue):
            assert (
                incoming_fragment['net']['datagram_tag'] !=
                outgoing_fragment['net']['datagram_tag']
            )

class TestFragmentForwarding(object):

    # index of the fragment that is the actual test input. A packet is divided
    # into four fragments, which are stored in a list. index-0 is the first
    # fragment, index-3 is the last one.
    TRIGGER_FRAGMENT_TYPE = [
        'missing_fragment',
        'last_fragment'
    ]
    @pytest.fixture(params=TRIGGER_FRAGMENT_TYPE)
    def trigger_fragment_type(self, request):
        return request.param

    def test_discard_vrb_entry_policy(
            self,
            sim_engine,
            fragmentation_ff_discard_vrb_entry_policy,
            trigger_fragment_type
        ):
        """Test discard_vrb_entry_policy
        - objective   : test if a specified policy is implemented correctly
        - precondition: form a 2-mote linear topology
        - precondition: make root to create a VRB table entry
        - expectation : if the trigger matches the policy, the entry should be removed
        - expectation : otherwise, the entry should remain in VRB table
        """
        sim_engine = sim_engine(
            diff_config = {
                'exec_numMotes'                            : 2,
                'app_pkLength'                             : 360,
                'fragmentation'                            : 'FragmentForwarding',
                'fragmentation_ff_discard_vrb_entry_policy': fragmentation_ff_discard_vrb_entry_policy,
            },
            force_initial_routing_and_scheduling_state = True
        )
        sim_settings = SimEngine.SimSettings.SimSettings()

        root = sim_engine.motes[0]
        leaf = sim_engine.motes[1]

        # prepare the first fragment and the trigger fragment
        # _send_a_single_packet() causes leaf to send a packet
        leaf.app._send_a_single_packet()
        fragments = []
        for frame in leaf.tsch.txQueue:
            if frame['type'] == d.PKT_TYPE_FRAG:
                fragments.append(frame)

        # inject the first fragment to root
        root.sixlowpan.recvPacket(fragments[0])
        assert get_memory_usage(root, sim_settings.fragmentation) == 1

        if trigger_fragment_type == 'missing_fragment':
            # skip injection of fragments[1], which is a missing fragment
            root.sixlowpan.recvPacket(fragments[2])
            if 'missing_fragment' in fragmentation_ff_discard_vrb_entry_policy:
                # the missing fragment should remove the entry
                assert get_memory_usage(root, sim_settings.fragmentation) == 0
            else:
                # the missing fragment shouldn't affect the entry
                assert get_memory_usage(root, sim_settings.fragmentation) == 1

        elif trigger_fragment_type == 'last_fragment':
            # inject all the fragments in order
            root.sixlowpan.recvPacket(fragments[1])
            root.sixlowpan.recvPacket(fragments[2])
            root.sixlowpan.recvPacket(fragments[3])

            if 'last_fragment' in fragmentation_ff_discard_vrb_entry_policy:
                # the last fragment should remove the entry
                assert get_memory_usage(root, sim_settings.fragmentation) == 0
            else:
                # the last fragment shouldn't affect the entry
                assert get_memory_usage(root, sim_settings.fragmentation) == 1
