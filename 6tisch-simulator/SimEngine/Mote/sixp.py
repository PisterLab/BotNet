"""6top Protocol (6P) module

See SchedulingFunctionTwoStep class and SchedulingFunctionThreeStep class that
are implemented in test/test_sixp.py to get an insight of how to implement a
scheduling function with the SixP APIs defined here. SchedulingFunctionMSF
implemented in sf.py is another example to see.
"""
from __future__ import absolute_import

# =========================== imports =========================================

from builtins import range
from builtins import object
import copy
import random

# Mote sub-modules
from . import MoteDefines as d

# Simulator-wide modules
import SimEngine

# =========================== defines =========================================

class TransactionAdditionError(Exception):
    pass

# =========================== helpers =========================================

# =========================== body ============================================

class SixP(object):

    def __init__(self, mote):

        # store params
        self.mote              = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine            = SimEngine.SimEngine.SimEngine()
        self.settings          = SimEngine.SimSettings.SimSettings()
        self.log               = SimEngine.SimLog.SimLog().log

        # local variables
        self.seqnum_table      = {} # indexed by neighbor_id
        self.transaction_table = {} # indexed by [initiator, responder]

    # ======================= public ==========================================

    def clear_transaction_table(self):
        for transaction in [self.transaction_table[key]
                            for key in self.transaction_table]:
            transaction.invalidate()

    def recv_packet(self, packet):

        # log
        self.log(
            SimEngine.SimLog.LOG_SIXP_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet':   packet
            }
        )

        if   packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_REQUEST:
            self._recv_request(packet)
        elif packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_RESPONSE:
            self._recv_response(packet)
        elif packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_CONFIRMATION:
            self._recv_confirmation(packet)
        else:
            raise Exception()

    def recv_mac_ack(self, packet):
        # identify a transaction instance to proceed
        transaction = self._find_transaction(packet)

        if transaction is None:
            # ignore this ACK
            return

        if (
                (packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_REQUEST)
                and
                (packet[u'app'][u'code'] != d.SIXP_CMD_CLEAR)
            ):
            self.mote.sixp.increment_seqnum(packet[u'mac'][u'dstMac'])

        if (
                (
                    (packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_RESPONSE)
                    and
                    (transaction.type == d.SIXP_TRANSACTION_TYPE_2_STEP)
                )
                or
                (
                    (packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_CONFIRMATION)
                    and
                    (transaction.type == d.SIXP_TRANSACTION_TYPE_3_STEP)
                )
            ):
            # complete the transaction
            transaction.complete()

            # invoke callback
            transaction.invoke_callback(
                event  = d.SIXP_CALLBACK_EVENT_MAC_ACK_RECEPTION,
                packet = packet
            )
        else:
            # do nothing
            pass

    def send_request(
            self,
            dstMac,
            command,
            metadata           = None,
            cellOptions        = None,
            numCells           = None,
            cellList           = None,
            relocationCellList = None,
            candidateCellList  = None,
            offset             = None,
            maxNumCells        = None,
            payload            = None,
            callback           = None,
            timeout_seconds    = None
        ):

        # create a packet
        packet = self._create_packet(
            dstMac             = dstMac,
            msgType            = d.SIXP_MSG_TYPE_REQUEST,
            code               = command,
            metadata           = metadata,
            cellOptions        = cellOptions,
            numCells           = numCells,
            cellList           = cellList,
            relocationCellList = relocationCellList,
            candidateCellList  = candidateCellList,
            offset             = offset,
            maxNumCells        = maxNumCells,
            payload            = payload
        )

        # create & start a transaction
        try:
            transaction = SixPTransaction(self.mote, packet)
        except TransactionAdditionError:
            # there are another transaction in process; cannot send this request
            callback(
                event  = d.SIXP_CALLBACK_EVENT_FAILURE,
                packet = packet
            )
        else:
            # ready to send the packet
            transaction.start(callback, timeout_seconds)

            # reset the next sequence number for the peer to 0 when the request
            # is CLEAR
            if command == d.SIXP_CMD_CLEAR:
                self.reset_seqnum(dstMac)

            # enqueue
            # the packet is saved for the callback, which is called
            # when the packet fails to be enqueued
            original_packet = copy.deepcopy(packet)
            self._tsch_enqueue(packet)

            if packet:
                # update transaction using the packet that has a valid
                # seqnum in the MAC header
                transaction.request = copy.deepcopy(packet)
            elif callback:
                # the packet could not be queued
                callback(
                    event  = d.SIXP_CALLBACK_EVENT_FAILURE,
                    packet = original_packet
                )

    def send_response(
            self,
            dstMac,
            return_code,
            seqNum          = None,
            numCells        = None,
            cellList        = None,
            payload         = None,
            callback        = None,
            timeout_seconds = None
        ):

        packet = self._create_packet(
            dstMac   = dstMac,
            msgType  = d.SIXP_MSG_TYPE_RESPONSE,
            code     = return_code,
            seqNum   = seqNum,
            numCells = numCells,
            cellList = cellList,
            payload  = payload,
        )

        # if seqNum is specified, we assume we don't have a valid transaction
        # for the response.
        if seqNum is not None:
            # do nothing
            transaction = None
        else:
            # update the transaction
            transaction = self._find_transaction(packet)
            assert transaction is not None

            # A corresponding transaction instance is supposed to be created
            # when it receives the request. its timer is restarted with the
            # specified callback and timeout_seconds now.
            transaction.start(callback, timeout_seconds)

        # enqueue
        self._tsch_enqueue(packet)
        if transaction:
            # keep the response packet in case of abortion
            transaction.response = copy.deepcopy(packet)

    def send_confirmation(
            self,
            dstMac,
            return_code,
            numCells = None,
            cellList = None,
            payload  = None,
            callback = None
        ):

        packet = self._create_packet(
            dstMac   = dstMac,
            msgType  = d.SIXP_MSG_TYPE_CONFIRMATION,
            code     = return_code,
            numCells = numCells,
            cellList = cellList,
            payload  = payload
        )

        # update the transaction
        transaction = self._find_transaction(packet)
        transaction.set_callback(callback)

        # enqueue
        self._tsch_enqueue(packet)

        # keep the confirmation packet
        transaction.confirmation = copy.deepcopy(packet)

    def add_transaction(self, transaction):
        if transaction.key in self.transaction_table:
            raise TransactionAdditionError()
        else:
            self.transaction_table[transaction.key] = transaction

    def delete_transaction(self, transaction):
        if transaction.key in self.transaction_table:
            assert transaction == self.transaction_table[transaction.key]
            del self.transaction_table[transaction.key]
        else:
            # do nothing if the transaction is not found in the table
            pass

    def abort_transaction(self, initiator_mac_addr, responder_mac_addr):
        # make sure we have a transaction to abort
        dummy_packet = {
            u'mac': {
                u'srcMac': initiator_mac_addr,
                u'dstMac': responder_mac_addr
            },
            u'app': {u'msgType': d.SIXP_MSG_TYPE_REQUEST}
        }
        transaction_key = SixPTransaction.get_transaction_key(dummy_packet)
        transaction = self.transaction_table[transaction_key]
        assert transaction is not None
        transaction.invoke_callback(
            event  = d.SIXP_CALLBACK_EVENT_ABORTED,
            packet = transaction.last_packet
        )

        transaction.invalidate()
        if transaction.isInitiator:
            if transaction.confirmation is not None:
                packet_in_tx_queue = transaction.confirmation
            else:
                packet_in_tx_queue = transaction.request
        else:
            packet_in_tx_queue = transaction.response

        self.mote.tsch.dequeue(packet_in_tx_queue)
        self.log(
            SimEngine.SimLog.LOG_SIXP_TRANSACTION_ABORTED,
            {
                u'_mote_id': self.mote.id,
                u'srcMac'  : transaction.initiator,
                u'dstMac'  : transaction.peerMac,
                u'seqNum'  : transaction.seqNum,
                u'cmd'     : transaction.request[u'app'][u'code']
            }
        )

        self.increment_seqnum(transaction.peerMac)

    def increment_seqnum(self, peerMac):
        assert peerMac in list(self.seqnum_table.keys())
        self.seqnum_table[peerMac] += 1
        if self.seqnum_table[peerMac] == 0x100:
            # SeqNum is two-octet long and the value of 0 is treated specially
            # as the special (initial) value. Then, the next value of 0xFF
            # (255) is 0x01 (1).
            self.seqnum_table[peerMac] = 1

    # ======================= private ==========================================

    def _tsch_enqueue(self, packet):
        self.log(
            SimEngine.SimLog.LOG_SIXP_TX,
            {
                u'_mote_id': self.mote.id,
                u'packet':   packet
            }
        )
        self.mote.tsch.enqueue(packet, priority=True)

    def _recv_request(self, request):
        # identify a transaction instance to proceed
        transaction = self._find_transaction(request)

        if transaction is None:
            # create a new transaction instance for the incoming request
            try:
                transaction = SixPTransaction(self.mote, request)
                # start the timer now. callback and timeout_seconds
                # can be set in send_response()
                transaction.start(
                    callback        = None,
                    timeout_seconds = None
                )
            except TransactionAdditionError:
                # SixPTransaction() would raise an exception when there is a
                # state mismatch between the initiator and the responder after
                # a CLEAR transaction, where CLEAR transaction expires on the
                # initiator and the transaction is alive on the
                # responder. Then, the initiator issues another request which
                # has SeqNum 1, but the responder still has the transaction of
                # CLEAR with SeqNum 0. In such a case, SixPTransaction() raises
                # an exception we will respond with RC_ERR_BUSY using SeqNum of
                # the incoming request.
                self.send_response(
                    dstMac      = request[u'mac'][u'srcMac'],
                    return_code = d.SIXP_RC_ERR_BUSY,
                    seqNum      = request[u'app'][u'seqNum']
                )
            else:
                peerMac = transaction.get_peerMac()
                if self._is_schedule_inconsistency_detected(transaction):
                    # schedule inconsistency is detected; respond with
                    # RC_ERR_SEQNUM
                    self.send_response(
                        dstMac      = peerMac,
                        return_code = d.SIXP_RC_ERR_SEQNUM
                    )
                    self.mote.sf.detect_schedule_inconsistency(peerMac)
                else:
                    if request[u'app'][u'code'] == d.SIXP_CMD_CLEAR:
                        # reset SeqNum when it's a CLEAR request
                        self.reset_seqnum(request[u'mac'][u'srcMac'])
                    else:
                        # increment SeqNum managed internally; this could be
                        # seen not aligned with the text of Section 3.4.6,
                        # shown below:
                        #
                        #    Similarly, a node B increments the SeqNum by
                        #    exactly 1 after having received the link-layer
                        #    acknowledgment for the 6P Response (2-step 6P
                        #    Transaction), or after having sent the link-layer
                        #    acknowledgment for the 6P Confirmation (3-step 6P
                        #    Transaction) .
                        #
                        # However, this is necessary to avoid ERR_SEQNUM on the
                        # next request when this transaction ends with timeout.
                        self.mote.sixp.increment_seqnum(peerMac)
                    # pass the incoming packet to the scheduling function
                    self.mote.sf.recv_request(request)
        else:
            # The incoming request should be duplicate one or should be a new
            # one even though the previous transaction is not completed; we
            # treat this packet as the latter case, if the incoming request is
            # not identical to the one we received before. Otherwise, a
            # response packet sent to the initiator will be handled in
            # different ways between the peers. The initiator thinks it's for
            # the second request, the responder thinks it's for the first
            # request.
            if request == transaction.request:
                # treat the incoming packet as duplicate one; ignore it
                pass
            else:
                # it seems the initiator has already terminated the transaction
                # by timeout and sent a request for a new transaction. Respond
                # with RC_ERR_BUSY.
                self.send_response(
                    dstMac      = request[u'mac'][u'srcMac'],
                    return_code = d.SIXP_RC_ERR_BUSY,
                )
                # terminate the outstanding transaction and call the timeout
                # handler. the method of timeout_handler() does everything for
                # us including removing the scheduled timer task.
                transaction.timeout_handler()

    def _recv_response(self, response):
        self.transaction_table
        transaction = self._find_transaction(response)
        if transaction is None:
            # Cannot find an corresponding transaction; ignore this packet
            pass
        else:
            # complete the transaction if necessary
            if transaction.type == d.SIXP_TRANSACTION_TYPE_2_STEP:
                transaction.complete()
            elif transaction.type == d.SIXP_TRANSACTION_TYPE_3_STEP:
                # the transaction is not finished yet
                pass
            else:
                # never happens
                raise Exception()

            # invoke callback
            transaction.invoke_callback(
                event  = d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION,
                packet = response
            )

    def _recv_confirmation(self, confirmation):
        transaction = self._find_transaction(confirmation)
        if transaction is None:
            # Cannot find an corresponding transaction; ignore this packet
            pass
        else:
            if transaction.type == d.SIXP_TRANSACTION_TYPE_2_STEP:
                # This shouldn't happen; ignore this packet
                pass
            elif transaction.type == d.SIXP_TRANSACTION_TYPE_3_STEP:
                # complete the transaction
                transaction.complete()
            else:
                # never happens
                raise Exception()

            # pass this to the scheduling function
            transaction.invoke_callback(
                event  = d.SIXP_CALLBACK_EVENT_PACKET_RECEPTION,
                packet = confirmation
            )

    def _create_packet(
            self,
            dstMac,
            msgType,
            code,
            seqNum             = None,
            metadata           = None,
            cellOptions        = None,
            numCells           = None,
            cellList           = None,
            relocationCellList = None,
            candidateCellList  = None,
            offset             = None,
            maxNumCells        = None,
            payload            = None
        ):
        packet = {
            u'type'       : d.PKT_TYPE_SIXP,
            u'mac': {
                u'srcMac' : self.mote.get_mac_addr(),
                u'dstMac' : dstMac
            },
            u'app': {
                u'msgType': msgType,
                u'code'   : code,
                u'seqNum' : None
            }
        }

        if   msgType == d.SIXP_MSG_TYPE_REQUEST:
            # put the next SeqNum
            packet[u'app'][u'seqNum'] = self._get_seqnum(dstMac)

            # command specific
            if (
                    (code == d.SIXP_CMD_ADD)
                    or
                    (code == d.SIXP_CMD_DELETE)
                ):
                packet[u'app'][u'metadata']           = metadata
                packet[u'app'][u'cellOptions']        = cellOptions
                packet[u'app'][u'numCells']           = numCells
                packet[u'app'][u'cellList']           = cellList
            elif code == d.SIXP_CMD_RELOCATE:
                packet[u'app'][u'metadata']           = metadata
                packet[u'app'][u'cellOptions']        = cellOptions
                packet[u'app'][u'numCells']           = numCells
                packet[u'app'][u'relocationCellList'] = relocationCellList
                packet[u'app'][u'candidateCellList']  = candidateCellList
            elif code == d.SIXP_CMD_COUNT:
                packet[u'app'][u'metadata']           = metadata
                packet[u'app'][u'cellOptions']        = cellOptions
            elif code == d.SIXP_CMD_LIST:
                packet[u'app'][u'metadata']           = metadata
                packet[u'app'][u'cellOptions']        = cellOptions
                packet[u'app'][u'offset']             = offset
                packet[u'app'][u'maxNumCells']        = maxNumCells
            elif code == d.SIXP_CMD_CLEAR:
                packet[u'app'][u'metadata']           = metadata
            elif code == d.SIXP_CMD_SIGNAL:
                packet[u'app'][u'metadata']           = metadata
                packet[u'app'][u'payload']            = payload
            else:
                raise NotImplementedError()

        elif msgType in [
                d.SIXP_MSG_TYPE_RESPONSE,
                d.SIXP_MSG_TYPE_CONFIRMATION
            ]:
            transaction = self._find_transaction(packet)
            assert transaction is not None

            # put SeqNum of request unless it's requested to use a specific
            # value.
            if seqNum is None:
                packet[u'app'][u'seqNum'] = transaction.request[u'app'][u'seqNum']
            else:
                assert isinstance(seqNum, int)
                assert seqNum >= 0
                assert seqNum < 256
                packet[u'app'][u'seqNum'] = seqNum

            command = transaction.request[u'app'][u'code']
            if (
                    (command == d.SIXP_CMD_ADD)
                    or
                    (command == d.SIXP_CMD_DELETE)
                    or
                    (command == d.SIXP_CMD_RELOCATE)
                    or
                    (command == d.SIXP_CMD_LIST)
                ):
                packet[u'app'][u'cellList'] = cellList
            elif command == d.SIXP_CMD_COUNT:
                packet[u'app'][u'numCells'] = numCells
            elif command == d.SIXP_CMD_CLEAR:
                # no additional field
                pass
            elif command == d.SIXP_CMD_SIGNAL:
                packet[u'app'][u'payload']  = payload

        else:
            # shouldn't come here
            raise Exception()

        return packet

    def _get_seqnum(self, peerMac):
        if peerMac not in list(self.seqnum_table.keys()):
            # the initial value of SeqNum is 0
            self.reset_seqnum(peerMac)
            return 0
        else:
            return self.seqnum_table[peerMac]

    def reset_seqnum(self, peerMac):
        self.seqnum_table[peerMac] = 0

    def _find_transaction(self, packet):
        transaction_key = SixPTransaction.get_transaction_key(packet)

        if transaction_key in self.transaction_table:
            transaction = self.transaction_table[transaction_key]
            request = transaction.request
            if (
                    (packet[u'app'][u'seqNum'] is None)
                    or
                    (packet[u'app'][u'seqNum'] == request[u'app'][u'seqNum'])
                ):
                # The input packet has the same seqNum as the request has. This
                # is a valid packet for this transaction
                pass
            else:
                # The input packet is an invalid packet for this transaction
                transaction = None
        else:
            transaction = None

        return transaction

    def _is_schedule_inconsistency_detected(self, transaction):
        # draft-ietf-6tisch-6top-protocol-12 says:
        #   A node computes the expected SeqNum field for the next 6P
        #   Transaction. If a node receives a 6P Request with a SeqNum value
        #   that is not the expected one, it has detected an inconsistency.
        #
        # although the expression of "expected" seems ambiguous, this shouldn't
        # mean the received SeqNum value and the SeqNum maintained by the
        # receiving mote are supposed to be identical.

        request = transaction.request
        peerMac = request[u'mac'][u'srcMac']

        if (
                (request[u'app'][u'code'] != d.SIXP_CMD_CLEAR)
                and
                (
                    (
                        (request[u'app'][u'seqNum'] == 0)
                        and
                        (self._get_seqnum(peerMac) != 0)
                    )
                    or
                    (
                        (request[u'app'][u'seqNum'] != 0)
                        and
                        (self._get_seqnum(peerMac) == 0)
                    )
                )
            ):
            returnVal = True
        else:
            returnVal = False

        return returnVal


class SixPTransaction(object):

    def __init__(self, mote, request):

        # sanity check
        assert request[u'type']           == d.PKT_TYPE_SIXP
        assert request[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_REQUEST

        # keep external instances
        self.mote             = mote
        self.engine           = SimEngine.SimEngine.SimEngine()
        self.settings         = SimEngine.SimSettings.SimSettings()
        self.log              = SimEngine.SimLog.SimLog().log

        # local variables
        self.request          = copy.deepcopy(request)
        self.response         = None
        self.confirmation     = None
        self.callback         = None
        self.type             = self._determine_transaction_type()
        self.key              = self.get_transaction_key(request)
        self.is_valid         = False

        # for quick access
        self.seqNum           = request[u'app'][u'seqNum']
        self.initiator        = request[u'mac'][u'srcMac']
        self.responder        = request[u'mac'][u'dstMac']
        self.isInitiator      = self.mote.is_my_mac_addr(request[u'mac'][u'srcMac'])
        if self.isInitiator:
            self.peerMac      = self.responder
        else:
            self.peerMac      = self.initiator
        self.event_unique_tag = u'{0}-{1}-{2}-{3}'.format(
            self.mote.id,
            self.initiator,
            self.responder,
            '6P-transaction-timeout'
        )

        # register itself to sixp
        self.mote.sixp.add_transaction(self)
        self.is_valid = True

    # ======================= public ==========================================

    @staticmethod
    def get_transaction_key(packet):
        if (
                (packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_REQUEST)
                or
                (packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_CONFIRMATION)
            ):
            initiator = packet[u'mac'][u'srcMac']
            responder = packet[u'mac'][u'dstMac']
        elif packet[u'app'][u'msgType'] == d.SIXP_MSG_TYPE_RESPONSE:
            initiator = packet[u'mac'][u'dstMac']
            responder = packet[u'mac'][u'srcMac']
        else:
            # shouldn't come here
            raise Exception()

        return u'{0}-{1}'.format(initiator, responder)

    @property
    def last_packet(self):
        if self.confirmation:
            last_packet = self.confirmation
        elif self.response:
            last_packet = self.response
        else:
            last_packet = self.request
        return last_packet

    def get_peerMac(self):
        return self.peerMac

    def set_callback(self, callback):
        self.callback = callback

    def start(self, callback, timeout_seconds):
        self.set_callback(callback)

        if timeout_seconds is None:
            # use the default timeout value
            timeout_seconds = self._get_default_timeout_seconds()

        self.engine.scheduleIn(
            delay          = timeout_seconds,
            cb             = self.timeout_handler,
            uniqueTag      = self.event_unique_tag,
            intraSlotOrder = d.INTRASLOTORDER_STACKTASKS,
        )

    def complete(self):
        self.log(
            SimEngine.SimLog.LOG_SIXP_TRANSACTION_COMPLETED,
            {
                u'_mote_id': self.mote.id,
                u'peerMac' : self.peerMac,
                u'seqNum'  : self.seqNum,
                u'cmd'     : self.request[u'app'][u'code']
            }
        )

        # invalidate itself
        self.invalidate()

    def invoke_callback(self, event, packet):
        assert packet is not None

        if self.callback is not None:
            self.callback(event, packet)

    def timeout_handler(self):
        # check whether the transaction has completed at the same ASN as this
        # timeout. if this is the case, we do nothing.
        if self.isInitiator:
            srcMac = self.initiator
            dstMac = self.peerMac
        else:
            srcMac = self.peerMac
            dstMac = self.responder

        if self.is_valid is True:
            self.log(
                SimEngine.SimLog.LOG_SIXP_TRANSACTION_TIMEOUT,
                {
                    u'_mote_id': self.mote.id,
                    u'srcMac'  : srcMac,
                    u'dstMac'  : dstMac,
                    u'seqNum'  : self.seqNum,
                    u'cmd'     : self.request[u'app'][u'code']
                }
            )

            self.invalidate()

            # remove a pending frame in TX queue if necessary
            self.mote.tsch.remove_packets_in_tx_queue(
                type   = d.PKT_TYPE_SIXP,
                dstMac = self.peerMac
            )

            # need to invoke the callback after the invalidation;
            # otherwise, a new transaction to the same peer would fail
            # due to duplicate (concurrent) transaction.
            self.invoke_callback(
                event  = d.SIXP_CALLBACK_EVENT_TIMEOUT,
                packet = self.last_packet
            )
        else:
            # the transaction has already been invalidated; do nothing here.
            pass

    # ======================= private ==========================================

    def invalidate(self):
        # remove its timeout event if it exists
        self.engine.removeFutureEvent(self.event_unique_tag)

        # delete the transaction from the 6P transaction table
        self.mote.sixp.delete_transaction(self)

        self.is_valid = False

    def _determine_transaction_type(self):
        if (
                (
                    (self.request[u'app'][u'code'] == d.SIXP_CMD_ADD)
                    and
                    (len(self.request[u'app'][u'cellList']) == 0)
                )
                or
                (
                    (self.request[u'app'][u'code'] == d.SIXP_CMD_DELETE)
                    and
                    (len(self.request[u'app'][u'cellList']) == 0)
                )
                or
                (
                    (self.request[u'app'][u'code'] == d.SIXP_CMD_RELOCATE)
                    and
                    (len(self.request[u'app'][u'candidateCellList']) == 0)
                )
            ):
            transaction_type = d.SIXP_TRANSACTION_TYPE_3_STEP
        else:
            transaction_type = d.SIXP_TRANSACTION_TYPE_2_STEP

        return transaction_type

    def _get_default_timeout_seconds(self):

        # draft-ietf-6tisch-6top-protocol-11 doesn't define the default timeout
        # value.

        # When the mote has the minimal shared cell alone to
        # communicate with its peer, one-way message delay could be the largest
        # value. The first transmission could happen 101 slots after the frame
        # is enqueued. After that, retransmissions could happen. We don't the
        # current TSCH TX queue length to calculate the possible maximum delay
        # at this moment. It may be better to do so.
        be = d.TSCH_MIN_BACKOFF_EXPONENT
        be_list = []
        assert self.mote.tsch.max_tx_retries != float('inf')
        for i in range(self.mote.tsch.max_tx_retries):
            be_list.append(be)
            be += 1
            if d.TSCH_MAX_BACKOFF_EXPONENT < be:
                be = d.TSCH_MAX_BACKOFF_EXPONENT
        one_way_delay = (
            self.settings.tsch_slotframeLength *
            self.settings.tsch_slotDuration *
            self.mote.tsch.max_tx_retries *
            sum(be_list)
        )

        if   (
                (self.type == d.SIXP_TRANSACTION_TYPE_2_STEP)
                and
                (self.isInitiator is False)
            ):
            # only round trip need to complete the transaction
            num_round_trips = 1
        elif (
                (
                    (self.type == d.SIXP_TRANSACTION_TYPE_2_STEP)
                    and
                    (self.isInitiator is True)
                )
                or
                (
                    (self.type == d.SIXP_TRANSACTION_TYPE_3_STEP)
                    and
                    (self.isInitiator is False)
                )
            ):
            # two round trips need to complete the transaction
            num_round_trips = 2
        elif (
                (self.type == d.SIXP_TRANSACTION_TYPE_3_STEP)
                and
                (self.isInitiator is True)
            ):
            # three round trips need to complete the transaction
            num_round_trips = 3
        else:
            raise Exception()

        return one_way_delay * num_round_trips
