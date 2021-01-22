from __future__ import absolute_import
from builtins import object
import copy
import types

import pytest

from . import test_utils as u
import SimEngine.Mote.MoteDefines as d
from SimEngine.Mote.sf import SchedulingFunctionBase
from SimEngine         import SimLog

# =========================== helpers =========================================

COMMON_SIM_ENGINE_ARGS = {
    'diff_config': {
        'exec_numMotes'           : 2,
        'sf_class'                : 'SFNone',
        'conn_class'              : 'Linear',
        'app_pkPeriod'            : 0,
        'tsch_probBcast_ebProb'   : 0
    },
    'force_initial_routing_and_scheduling_state': True
}


class SchedulingFunctionTest(SchedulingFunctionBase):
    """Base class for scheduling functions defined here
    """

    # ======================= static values====================================

    DUMMY_CELL_LIST = {
        'slotOffset'   : 1,
        'channelOffset': 2
    }

    # ======================= public ==========================================

    def start(self):
        pass

    def stop(self):
        pass

    def indication_neighbor_added(self,neighbor):
        pass

    def indication_neighbor_deleted(self,neighbor):
        pass

    def indication_tx_cell_elapsed(self, cell, sent_packet):
        pass

    def indication_rx_cell_elapsed(self, cell, received_packet):
        pass

    def indication_parent_change(self, old_parent, new_parent):
        pass

    def detect_schedule_inconsistency(self, peerMac):
        pass

    def recv_request(self, packet):
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_REQUEST
        assert packet['app']['code'] in [
            d.SIXP_CMD_ADD,
            d.SIXP_CMD_DELETE,
            d.SIXP_CMD_RELOCATE
        ]

        self.mote.sixp.send_response(
            dstMac      = packet['mac']['srcMac'],
            return_code = d.SIXP_RC_SUCCESS,
            callback    = self._response_callback
        )

    def clear_to_send_EBs_DATA(self):
        return True

    # ======================= private ==========================================

    def _issue_add_request(self, peerMac, cellList):
        self.mote.sixp.send_request(
            dstMac   = peerMac,
            command  = d.SIXP_CMD_ADD,
            numCells = 0,
            cellList = cellList,
            callback = self._request_callback
        )

    def _issue_delete_request(self, peerMac, cellList):
        self.mote.sixp.send_request(
            dstMac   = peerMac,
            command  = d.SIXP_CMD_DELETE,
            numCells = 0,
            cellList = cellList,
            callback = self._request_callback
        )

    def _issue_relocate_request(self, peerMac, cellList):
        self.mote.sixp.send_request(
            dstMac             = peerMac,
            command            = d.SIXP_CMD_RELOCATE,
            numCells           = 0,
            relocationCellList = cellList,
            candidateCellList  = cellList,
            callback           = self._request_callback
        )

    def _request_callback(self, event, packet):
        raise NotImplementedError()

    @staticmethod
    def _response_callback(self, event, packet):
        raise NotImplementedError()


class SchedulingFunctionTwoStep(SchedulingFunctionTest):
    """This is an example scheduling function which supports 2-step
    ADD/DELETE/RELOCATE transactions.
    """
    # ======================= public ==========================================
    def issue_add_request(self, peerMac):
        self._issue_add_request(
            peerMac  = peerMac,
            cellList = self.DUMMY_CELL_LIST
        )

    def issue_delete_request(self, peerMac):
        self._issue_delete_request(
            peerMac  = peerMac,
            cellList = self.DUMMY_CELL_LIST
        )

    def issue_relocate_request(self, peerMac):
        self._issue_relocate_request(
            peerMac  = peerMac,
            cellList = self.DUMMY_CELL_LIST
        )

    def _request_callback(self, event, packet):
        # In a 2-step transaction, request_callback will receive
        # SIXP_CALLBACK_EVENT_PACKET_RECEPTION with a response packet
        assert event                    == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
        assert packet['app']['code']    == d.SIXP_RC_SUCCESS

    def _response_callback(self, event, packet):
        # In a 2-step transaction, response_callback will receive
        # SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION for the response packet
        assert event == d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
        assert packet['app']['code']    == d.SIXP_RC_SUCCESS


class SchedulingFunctionThreeStep(SchedulingFunctionTest):
    """This is an example scheduling function which supports 3-step
    ADD/DELETE/RELOCATE transactions. These request packet has empty
    cell list.
    """
    # ======================= public ==========================================
    def issue_add_request(self, peerMac):
        self._issue_add_request(
            peerMac  = peerMac,
            cellList = [] # empty cell list
        )

    def issue_delete_request(self, peerMac):
        self._issue_delete_request(
            peerMac  = peerMac,
            cellList = [] # empty cell list
        )

    def issue_relocate_request(self, peerMac):
        self._issue_relocate_request(
            peerMac  = peerMac,
            cellList = [] # empty cell list
        )

    def _request_callback(self, event, packet):
        # In a 3-step transaction, request_callback will receive
        # SIXP_CALLBACK_EVENT_PACKET_RECEPTION with a response packet as well
        # as in a 2-step transaction.
        assert event                    == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
        assert packet['app']['code']    == d.SIXP_RC_SUCCESS

        self.mote.sixp.send_confirmation(
            dstMac      = packet['mac']['srcMac'],
            return_code = d.SIXP_RC_SUCCESS,
            callback    = self._confirmation_callback
        )

    def _response_callback(self, event, packet):
        # In a 3-step transaction, response_callback will receive
        # SIXP_CALLBACK_EVENT_PACKET_RECEPTION with a *confirmation* packet
        # instead of SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION for the response
        assert event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_CONFIRMATION
        assert packet['app']['code']    == d.SIXP_RC_SUCCESS

    def _confirmation_callback(self, event, packet):
        # confirmation_callback will receive
        # SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION with the confirmation packet
        assert event == d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION
        assert packet['type']           == d.PKT_TYPE_SIXP
        assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_CONFIRMATION
        assert packet['app']['code']    == d.SIXP_RC_SUCCESS


class SchedulingFunctionTwoStepForAbortion(SchedulingFunctionTwoStep):
    def __init__(self, mote):
        super(SchedulingFunctionTwoStepForAbortion, self).__init__(mote)
        self.received_aborted_event = False

    def _request_callback(self, event, packet):
        if event == d.SIXP_CALLBACK_EVENT_ABORTED:
            self.received_aborted_event = True
        else:
            super(SchedulingFunctionTwoStepForAbortion, self)._request_callback(
                event,
                packet
            )

    def _response_callback(self, event, packet):
        if event == d.SIXP_CALLBACK_EVENT_ABORTED:
            self.received_aborted_event = True
        else:
            super(SchedulingFunctionTwoStepForAbortion, self)._response_callback(
                event,
                packet
            )


class SchedulingFunctionThreeStepForAbortion(SchedulingFunctionThreeStep):
    def __init__(self, mote):
        super(SchedulingFunctionThreeStepForAbortion, self).__init__(mote)
        self.received_aborted_event = False

    def _request_callback(self, event, packet):
        if event == d.SIXP_CALLBACK_EVENT_ABORTED:
            self.received_aborted_event = True
        else:
            super(SchedulingFunctionThreeStepForAbortion, self)._request_callback(
                event,
                packet
            )

    def _confirmation_callback(self, event, packet):
        if event == d.SIXP_CALLBACK_EVENT_ABORTED:
            self.received_aborted_event = True
        else:
            super(SchedulingFunctionThreeStepForAbortion, self)._confirmation_callback(
                event,
                packet
            )


def install_sf(motes, sf_class):
    for mote in motes:
        mote.sf = sf_class(mote)

# =========================== fixtures =========================================

SCHEDULING_FUNCTIONS = [
    SchedulingFunctionTwoStep,
    SchedulingFunctionThreeStep
]
@pytest.fixture(params=SCHEDULING_FUNCTIONS)
def scheduling_function(request):
    return request.param

# =========================== tests ===========================================


class TestTransaction(object):

    def test_transaciton_type(self, sim_engine, scheduling_function):

        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        # install the test scheduling function to the motes
        install_sf(sim_engine.motes, scheduling_function)

        # trigger an ADD transaction
        sim_engine.motes[0].sf.issue_add_request(sim_engine.motes[1].get_mac_addr())
        u.run_until_asn(sim_engine, 1000)

        # trigger a DELETE transaction
        sim_engine.motes[0].sf.issue_delete_request(sim_engine.motes[1].get_mac_addr())
        u.run_until_asn(sim_engine, sim_engine.getAsn() + 1000)

        # trigger a RELOCATE transaction
        sim_engine.motes[0].sf.issue_relocate_request(sim_engine.motes[1].get_mac_addr())
        u.run_until_asn(sim_engine, sim_engine.getAsn() + 1000)

        # done
        assert True

    def test_concurrent_transactions(self, sim_engine):
        """6P must return RC_ERR_BUSY when it receives a request from a peer
        with whom it has already another transaction in process.
        """

        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        # for quick access
        initiator = sim_engine.motes[0]
        responder = sim_engine.motes[1]

        # trigger an ADD transaction, which will terminate by timeout on the
        # initiator.sfinitiator's side
        initiator.sixp.send_request(
            dstMac          = responder.get_mac_addr(),
            command         = d.SIXP_CMD_ADD,
            cellList        = [],
            timeout_seconds = 2
        )

        # wait a little bit
        u.run_until_asn(sim_engine, 200)

        # now responder should have a transaction; issue a DELETE request,
        # which should cause RC_ERR_BUSY
        result = {'is_callback_called': False}
        def request_callback(event, packet):
            result['is_callback_called'] = True
            assert event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION
            assert packet['type'] == d.PKT_TYPE_SIXP
            assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
            assert packet['app']['code']    == d.SIXP_RC_ERR_BUSY
        initiator.sixp.send_request(
            dstMac   = responder.get_mac_addr(),
            command  = d.SIXP_CMD_DELETE,
            cellList = [],
            callback = request_callback
        )

        # wait a little bit
        u.run_until_asn(sim_engine, sim_engine.getAsn() + 200)

        assert result['is_callback_called'] is True

    def test_timeout(self, sim_engine):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        # for quick access
        mote_0 = sim_engine.motes[0]
        mote_1 = sim_engine.motes[1]

        # test timeout on the initiator side
        result = {'is_request_callback_called': False}
        def request_callback(event, packet):
            assert event  == d.SIXP_CALLBACK_EVENT_TIMEOUT
            assert packet
            result['is_request_callback_called'] = True
        mote_0.sixp.send_request(
            dstMac   = mote_1.get_mac_addr(),
            command  = d.SIXP_CMD_COUNT,
            callback = request_callback
        )

        # test timeout on the responder side
        result['is_response_callback_called'] = False
        def response_callback(event, packet):
            assert event  == d.SIXP_CALLBACK_EVENT_TIMEOUT
            assert packet
            result['is_response_callback_called'] = True
        def recv_request(self, packet):
            self.mote.sixp.send_response(
                dstMac      = packet['mac']['srcMac'],
                return_code = d.SIXP_RC_SUCCESS,
                callback    = response_callback
            )
            # remove the response
            self.mote.tsch.txQueue.pop(0)

        mote_1.sf.recv_request = types.MethodType(
            recv_request,
            mote_1.sf
        )

        # run the simulator
        u.run_until_end(sim_engine)

        assert result['is_request_callback_called']  is True
        assert result['is_response_callback_called'] is True

    def test_issue_188(self, sim_engine):
        """This test reproduces Issue #188

        An exception was raised when a mote receives a request which has
        a different SeqNum from one in a valid transaction it still
        has.
        """
        sim_engine = sim_engine(
            diff_config = {
                'exec_numSlotframesPerRun': 10,
                'exec_numMotes'           : 2,
                'sf_class'                : 'SFNone',
                'conn_class'              : 'Linear',
                'tsch_probBcast_ebProb'   : 0
            },
            force_initial_routing_and_scheduling_state = True
        )

        # for quick access
        root  = sim_engine.motes[0]
        hop_1 = sim_engine.motes[1]

        # step-0: set 1 (a non-zero value) to local SeqNum both of root and
        # hop_1
        root.sixp._get_seqnum(hop_1.get_mac_addr())       # create a SeqNum entry
        root.sixp.increment_seqnum(hop_1.get_mac_addr())  # increment the SeqNum
        hop_1.sixp._get_seqnum(root.get_mac_addr())       # create a SeqNum entry
        hop_1.sixp.increment_seqnum(root.get_mac_addr())  # increment the SeqNum

        # step-1: let hop_1 issue an ADD request. In order to make the
        # transaction expire on hop_1, set a shorter timeout value on hop_1's
        # side
        timeout_seconds = 0.01
        hop_1.sixp.send_request(
            dstMac          = root.get_mac_addr(),
            command         = d.SIXP_CMD_ADD,
            cellList        = [],
            timeout_seconds = timeout_seconds
        )

        # step-2: let root issue an CLEAR request when it receives an ADD
        # request from hop_1. Then, the root will have two transactions to
        # hop_1 with each direction.
        result = {'root_received_add_request': False}
        def recv_add_request(self, packet):
            assert packet['type']                  == d.PKT_TYPE_SIXP
            assert packet['app']['msgType']        == d.SIXP_MSG_TYPE_REQUEST
            assert packet['app']['code']           == d.SIXP_CMD_ADD

            if result['root_received_add_request'] is False:
                result['root_received_add_request'] = True

                # send a CLAER request to the responder
                self.mote.sixp.send_request(
                    dstMac   = hop_1.get_mac_addr(),
                    command  = d.SIXP_CMD_CLEAR
                )
            else:
                # do nothing
                pass
        root.sf.recv_request = types.MethodType(recv_add_request, root.sf)

        # step-3: let hop_1 issue another ADD request when it receives a CLAER
        # request from the hop_1. Then, the root will have two transactions to
        # the responder for each direction.
        result['hop_1_received_clear_request'] = False
        def recv_clear_request(self, packet):
            assert packet['type']                  == d.PKT_TYPE_SIXP
            assert packet['app']['msgType']        == d.SIXP_MSG_TYPE_REQUEST
            assert packet['app']['code']           == d.SIXP_CMD_CLEAR

            result['hop_1_received_clear_request'] = True

            # send a new ADD request, which causes an exception unless the
            # bugfix is in place.
            self.mote.sixp.send_request(
                dstMac   = root.get_mac_addr(),
                command  = d.SIXP_CMD_ADD,
                cellList = []
            )
        hop_1.sf.recv_request = types.MethodType(recv_clear_request, hop_1.sf)

        # run the simulator until the end; if there is no exception, it should
        # run through.
        u.run_until_end(sim_engine)

        assert result['root_received_add_request'] == True
        assert result['hop_1_received_clear_request'] == True

        # There should be one RC_ERR_BUSY from root
        logs     = u.read_log_file([SimLog.LOG_SIXP_TX['type']])
        rc_err_busy_logs = [
            l for l in logs if (
                (l['packet']['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE)
                and
                (l['packet']['app']['code']    == d.SIXP_RC_ERR_BUSY)
                and
                (root.is_my_mac_addr(l['packet']['mac']['srcMac']))
                and
                (hop_1.is_my_mac_addr(l['packet']['mac']['dstMac']))
            )
        ]
        assert len(rc_err_busy_logs) == 1

        # RC_ERR_BUSY should be sent to the ADD request with SeqNum of 0
        assert rc_err_busy_logs[0]['packet']['app']['seqNum'] == 0

    @pytest.fixture(
        params=[d.SIXP_MSG_TYPE_REQUEST, d.SIXP_MSG_TYPE_CONFIRMATION]
    )
    def fixture_msg_type(self, request):
        return request.param

    def test_abort_on_initiator(self, sim_engine, fixture_msg_type):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        install_sf(sim_engine.motes, SchedulingFunctionThreeStepForAbortion)
        root = sim_engine.motes[0]
        mote = sim_engine.motes[1]

        assert len(root.sixp.transaction_table) == 0
        assert len(root.tsch.txQueue) == 0

        root.sf.issue_add_request(mote.get_mac_addr())

        if fixture_msg_type == d.SIXP_MSG_TYPE_REQUEST:
            logs = u.read_log_file([SimLog.LOG_SIXP_TX['type']])
            assert len(logs) == 1
            assert logs[0]['_mote_id'] == root.id
            assert logs[0]['packet']['app']['msgType'] == (
                d.SIXP_MSG_TYPE_REQUEST
            )
        else:
            assert fixture_msg_type == d.SIXP_MSG_TYPE_CONFIRMATION
            u.run_until_asn(sim_engine, 102)

            # we should have two sixp.rx logs: one is for the request, the
            # other is for response
            logs = u.read_log_file([SimLog.LOG_SIXP_RX['type']])
            assert len(logs) == 2
            assert logs[0]['_mote_id'] == mote.id
            assert logs[1]['_mote_id'] == root.id

            # we should have three sixp.tx logs for each msg_type
            logs = u.read_log_file([SimLog.LOG_SIXP_TX['type']])
            assert len(logs) == 3
            assert logs[0]['_mote_id'] == root.id
            assert logs[1]['_mote_id'] == mote.id
            assert logs[2]['_mote_id'] == root.id
            assert logs[2]['packet']['app']['msgType'] == (
                d.SIXP_MSG_TYPE_CONFIRMATION
            )

        # abort the transaction on the initiator
        assert len(root.sixp.transaction_table) == 1
        assert len(root.tsch.txQueue) == 1

        # handler should receive the "aborted" event
        assert root.sf.received_aborted_event is False
        root.sixp.abort_transaction(
            initiator_mac_addr = root.get_mac_addr(),
            responder_mac_addr = mote.get_mac_addr()
        )
        assert root.sf.received_aborted_event is True

        assert len(root.sixp.transaction_table) == 0
        assert len(root.tsch.txQueue) == 0

    def test_abort_on_responder(self, sim_engine):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        install_sf(sim_engine.motes, SchedulingFunctionTwoStepForAbortion)
        root = sim_engine.motes[0]
        mote = sim_engine.motes[1]

        root.sf.issue_add_request(mote.get_mac_addr())
        u.run_until_asn(sim_engine, 101)

        # mote should receive the request
        logs = u.read_log_file([SimLog.LOG_SIXP_RX['type']])
        assert len(logs) == 1
        assert logs[0]['_mote_id'] == mote.id

        # we should have two sixp.tx logs: one is for the request, the other is
        # for response
        logs = u.read_log_file([SimLog.LOG_SIXP_TX['type']])
        assert len(logs) == 2
        assert logs[0]['_mote_id'] == root.id
        assert logs[1]['_mote_id'] == mote.id
        assert logs[1]['packet']['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE

        # abort the transaction on the responder
        assert len(mote.sixp.transaction_table) == 1
        assert len(mote.tsch.txQueue) == 1

        # handler should receive the "aborted" event
        assert mote.sf.received_aborted_event is False
        mote.sixp.abort_transaction(
            initiator_mac_addr = root.get_mac_addr(),
            responder_mac_addr = mote.get_mac_addr()
        )
        assert mote.sf.received_aborted_event is True

        assert len(mote.sixp.transaction_table) == 0
        assert len(mote.tsch.txQueue) == 0

class TestSeqNum(object):

    @pytest.fixture(params=[0, 1, 2, 100, 200, 254, 255])
    def initial_seqnum(self, request):
        return request.param

    def test_seqnum_increment(self, sim_engine, initial_seqnum):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        # install a test SF
        install_sf(sim_engine.motes, SchedulingFunctionTwoStep)

        # for quick access
        mote_0 = sim_engine.motes[0]
        mote_1 = sim_engine.motes[1]

        # set initial SeqNum
        mote_0.sixp.seqnum_table[mote_1.get_mac_addr()] = initial_seqnum
        mote_1.sixp.seqnum_table[mote_0.get_mac_addr()] = initial_seqnum

        # execute one transaction
        mote_0.sf.issue_add_request(mote_1.get_mac_addr())

        # wait a little bit
        u.run_until_asn(sim_engine, 500)

        # check the SeqNums both of the motes maintain
        if initial_seqnum == 255:
            expected_seqnum = 1
        else:
            expected_seqnum = initial_seqnum + 1
        assert mote_0.sixp.seqnum_table[mote_1.get_mac_addr()] == expected_seqnum
        assert mote_1.sixp.seqnum_table[mote_0.get_mac_addr()] == expected_seqnum

    def test_schedule_inconsistency(self, sim_engine, initial_seqnum):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)

        # for quick access
        mote_0 = sim_engine.motes[0]
        mote_1 = sim_engine.motes[1]

        # set initial SeqNum; mote_0 has zero, mote_1 has non-zero (1)
        mote_0.sixp.seqnum_table[mote_1.get_mac_addr()] = 0
        mote_1.sixp.seqnum_table[mote_0.get_mac_addr()] = 1

        # prepare assertion
        result = {'is_schedule_inconsistency_detected': False}
        def detect_schedule_inconsistency(self, peerMac):
            assert mote_0.is_my_mac_addr(peerMac)
            result['is_schedule_inconsistency_detected'] = True
        mote_1.sf.detect_schedule_inconsistency = types.MethodType(
            detect_schedule_inconsistency,
            mote_1.sf
        )

        # send a request which causes the responder to detect schedule
        # inconsistency. the initiator should receive RC_ERR_SEQNUM.
        result['is_rc_err_seqnum_received'] = False
        def request_callback(event, packet):
            assert event == d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION
            assert packet['app']['msgType'] == d.SIXP_MSG_TYPE_RESPONSE
            assert packet['app']['code']    == d.SIXP_RC_ERR_SEQNUM
            result['is_rc_err_seqnum_received'] = True
        mote_0.sixp.send_request(
            dstMac   = mote_1.get_mac_addr(),
            command  = d.SIXP_CMD_COUNT,
            callback = request_callback
        )

        # wait a little bit
        u.run_until_asn(sim_engine, 500)

        assert result['is_schedule_inconsistency_detected'] is True
        assert result['is_rc_err_seqnum_received']          is True

    def test_request_drop(self, sim_engine):
        sim_engine = sim_engine(**COMMON_SIM_ENGINE_ARGS)
        mote = sim_engine.motes[0]
        peer = sim_engine.motes[1]
        # make the mote not able to enqueue any packet
        mote.tsch.txQueueSize = 0
        mote.sixp.send_request(
            dstMac          = peer.get_mac_addr(),
            command         = d.SIXP_CMD_ADD,
            cellList        = [],
            timeout_seconds = 2
        )
        u.run_until_end(sim_engine)
