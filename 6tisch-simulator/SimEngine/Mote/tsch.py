"""
"""
from __future__ import absolute_import
from __future__ import division

# =========================== imports =========================================

from builtins import str
from builtins import filter
from builtins import range
from builtins import object
from past.utils import old_div
import copy
from itertools import chain
import random

import netaddr

# Mote sub-modules
from . import MoteDefines as d
from SimEngine.Mote.sf import SchedulingFunctionMSF

# Simulator-wide modules
import SimEngine

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

class Tsch(object):

    def __init__(self, mote):

        # store params
        self.mote = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine   = SimEngine.SimEngine.SimEngine()
        self.settings = SimEngine.SimSettings.SimSettings()
        self.log      = SimEngine.SimLog.SimLog().log

        # local variables
        self.slotframes       = {}
        self.txQueue          = []
        if self.settings.tsch_tx_queue_size >= 0:
            self.txQueueSize  = self.settings.tsch_tx_queue_size
        elif self.settings.tsch_tx_queue_size == -1:
            self.txQueueSize  = float('inf')
        else:
            raise ValueError(
                u'unsupported tx_queue_size: {0}'.format(
                    self.settings.tsch_tx_queue_size
                )
            )
        if self.settings.tsch_max_tx_retries >= 0:
            self.max_tx_retries = self.settings.tsch_max_tx_retries
        elif self.settings.tsch_max_tx_retries == -1:
            self.max_tx_retries = float('inf')
        else:
            raise ValueError(
                u'unsupported tsch_max_tx_retries: {0}'.format(
                    self.settings.tsch_max_tx_retries
                )
            )
        self.neighbor_table   = []
        self.pktToSend        = None
        self.waitingFor       = None
        self.active_cell      = None
        self.asnLastSync      = None
        self.isSync           = False
        self.join_proxy       = None
        self.iAmSendingEBs    = False
        self.clock            = Clock(self.mote)
        self.next_seqnum      = 0
        self.received_eb_list = {} # indexed by source mac address
        # backoff state
        self.backoff_exponent        = d.TSCH_MIN_BACKOFF_EXPONENT
        # pending bit
        self.pending_bit_enabled            = False
        self.args_for_next_pending_bit_task = None

        assert self.settings.phy_numChans <= len(d.TSCH_HOPPING_SEQUENCE)
        self.hopping_sequence = (
            d.TSCH_HOPPING_SEQUENCE[:self.settings.phy_numChans]
        )

        # install the default slotframe
        self.add_slotframe(
            slotframe_handle = 0,
            length           = self.settings.tsch_slotframeLength
        )

    #======================== public ==========================================

    # getters/setters

    def getIsSync(self):
        return self.isSync

    def setIsSync(self,val):
        # set
        self.isSync = val

        if self.isSync:
            # log
            self.log(
                SimEngine.SimLog.LOG_TSCH_SYNCED,
                {
                    "_mote_id":   self.mote.id,
                }
            )

            self.asnLastSync = self.engine.getAsn()
            if self.mote.dagRoot:
                # we don't need the timers
                pass
            else:
                self._start_keep_alive_timer()
                self._start_synchronization_timer()

            # start SF
            self.mote.sf.start()

            # transition: listeningForEB->active
            self.engine.removeFutureEvent(      # remove previously scheduled listeningForEB cells
                uniqueTag=(self.mote.id, u'_action_listeningForEB_cell')
            )
        else:
            # log
            self.log(
                SimEngine.SimLog.LOG_TSCH_DESYNCED,
                {
                    "_mote_id":   self.mote.id,
                }
            )
            # DAGRoot gets never desynchronized
            assert not self.mote.dagRoot

            self.stopSendingEBs()
            self.delete_minimal_cell()
            self.mote.sf.stop()
            self.mote.sixp.clear_transaction_table()
            self.mote.secjoin.setIsJoined(False)
            self.asnLastSync = None
            self.clock.desync()
            self._stop_keep_alive_timer()
            self._stop_synchronization_timer()
            self.txQueue = []
            self.received_eb_list = {}
            # we may have this timer task
            self.engine.removeFutureEvent(
                uniqueTag=(self.mote.id, u'tsch', u'wait_secjoin')
            )

            # transition: active->listeningForEB
            self.engine.removeFutureEvent(      # remove previously scheduled listeningForEB cells
                uniqueTag=(self.mote.id, u'_action_active_cell')
            )
            self.schedule_next_listeningForEB_cell()

    def get_busy_slots(self, slotframe_handle=0):
        if slotframe_handle in self.slotframes:
            return self.slotframes[slotframe_handle].get_busy_slots()
        else:
            return 0

    def get_available_slots(self, slotframe_handle=0):
        if slotframe_handle in self.slotframes:
            return self.slotframes[slotframe_handle].get_available_slots()
        else:
            return 0

    def get_cell(self, slot_offset, channel_offset, mac_addr, slotframe_handle=0):
        if slotframe_handle in self.slotframes:
            slotframe = self.slotframes[slotframe_handle]
            cells = slotframe.get_cells_by_slot_offset(slot_offset)
            for cell in cells:
                if (
                        (cell.channel_offset == channel_offset)
                        and
                        (cell.mac_addr == mac_addr)
                    ):
                    return cell
        return None

    def get_cells(self, mac_addr=None, slotframe_handle=None):
        if slotframe_handle:
            if slotframe_handle in self.slotframes:
                slotframe = self.slotframes[slotframe_handle]
                ret_val = slotframe.get_cells_by_mac_addr(mac_addr)
            else:
                ret_val = []
        else:
            ret_val = []
            for slotframe_handle in self.slotframes:
                slotframe = self.slotframes[slotframe_handle]
                ret_val += slotframe.get_cells_by_mac_addr(mac_addr)
        return ret_val

    def enable_pending_bit(self):
        self.pending_bit_enabled = True

    # slotframe
    def get_slotframe(self, slotframe_handle):
        if slotframe_handle in self.slotframes:
            return self.slotframes[slotframe_handle]
        else:
            return None

    def add_slotframe(self, slotframe_handle, length):
        assert slotframe_handle not in self.slotframes
        self.slotframes[slotframe_handle] = SlotFrame(
            mote_id          = self.mote.id,
            slotframe_handle = slotframe_handle,
            num_slots        = length
        )
        self.log(
            SimEngine.SimLog.LOG_TSCH_ADD_SLOTFRAME,
            {
                u'_mote_id'       : self.mote.id,
                u'slotFrameHandle': slotframe_handle,
                u'length'         : length
            }
        )

    def delete_slotframe(self, slotframe_handle):
        assert slotframe_handle in self.slotframes
        self.log(
            SimEngine.SimLog.LOG_TSCH_DELETE_SLOTFRAME,
            {
                u'_mote_id'       : self.mote.id,
                u'slotFrameHandle': slotframe_handle,
                u'length'         : self.slotframes[slotframe_handle].length
            }
        )
        del self.slotframes[slotframe_handle]

    # EB / Enhanced Beacon

    def startSendingEBs(self):
        self.iAmSendingEBs = True

    def stopSendingEBs(self):
        self.iAmSendingEBs = True

    def schedule_next_listeningForEB_cell(self):

        assert not self.getIsSync()

        # schedule at next ASN
        self.engine.scheduleAtAsn(
            asn              = self.engine.getAsn()+1,
            cb               = self._action_listeningForEB_cell,
            uniqueTag        = (self.mote.id, u'_action_listeningForEB_cell'),
            intraSlotOrder   = d.INTRASLOTORDER_STARTSLOT,
        )

    # minimal

    def add_minimal_cell(self):
        assert self.isSync

        # the minimal cell is allocated in slotframe 0
        self.addCell(
            slotOffset       = 0,
            channelOffset    = 0,
            neighbor         = None,
            cellOptions      = [
                d.CELLOPTION_TX,
                d.CELLOPTION_RX,
                d.CELLOPTION_SHARED
            ],
            slotframe_handle = 0,
            link_type        = d.LINKTYPE_ADVERTISING
        )

    def delete_minimal_cell(self):
        # the minimal cell should be allocated in slotframe 0
        self.deleteCell(
            slotOffset       = 0,
            channelOffset    = 0,
            neighbor         = None,
            cellOptions      = [
                d.CELLOPTION_TX,
                d.CELLOPTION_RX,
                d.CELLOPTION_SHARED
            ],
            slotframe_handle = 0
        )

    # schedule interface

    def addCell(
            self,
            slotOffset,
            channelOffset,
            neighbor,
            cellOptions,
            slotframe_handle=0,
            link_type = d.LINKTYPE_NORMAL
        ):

        assert isinstance(slotOffset, int)
        assert isinstance(channelOffset, int)
        assert isinstance(cellOptions, list)
        assert link_type not in [True, False]

        slotframe = self.slotframes[slotframe_handle]

        # add cell
        cell = Cell(
            slotOffset,
            channelOffset,
            cellOptions,
            neighbor,
            link_type
        )
        slotframe.add(cell)

        # reschedule the next active cell, in case it is now earlier
        if self.getIsSync():
            self._schedule_next_active_slot()

    def deleteCell(self, slotOffset, channelOffset, neighbor, cellOptions, slotframe_handle=0):
        assert isinstance(slotOffset, int)
        assert isinstance(channelOffset, int)
        assert isinstance(cellOptions, list)

        slotframe = self.slotframes[slotframe_handle]

        # find a target cell. if the cell is not scheduled, the following
        # raises an exception
        cell = self.get_cell(slotOffset, channelOffset, neighbor, slotframe_handle)
        assert cell.mac_addr == neighbor
        assert cell.options == cellOptions

        # delete cell
        slotframe.delete(cell)

        # reschedule the next active cell, in case it is now earlier
        if self.getIsSync():
            self._schedule_next_active_slot()

    # tx queue interface with upper layers

    @property
    def droppable_normal_packet_index(self):
        for rindex, packet in enumerate(reversed(self.txQueue)):
            if (
                    (packet[u'mac'][u'priority'] is False)
                    and
                    (self.pktToSend != packet)
                ):
                # return index of the packet
                return len(self.txQueue) - rindex - 1
        return None

    def enqueue(self, packet, priority=False):

        assert packet[u'type'] != d.PKT_TYPE_EB
        assert u'srcMac' in packet[u'mac']
        assert u'dstMac' in packet[u'mac']

        goOn = True

        # check there is space in txQueue
        assert len(self.txQueue) <= self.txQueueSize
        if (
                goOn
                and
                (len(self.txQueue) == self.txQueueSize)
                and
                (
                    (priority is False)
                    or
                    self.droppable_normal_packet_index is None
                )
            ):
            # my TX queue is full

            # drop
            self.mote.drop_packet(
                packet  = packet,
                reason  = SimEngine.SimLog.DROPREASON_TXQUEUE_FULL
            )

            # couldn't enqueue
            goOn = False

        # check that I have cell to transmit on
        if goOn:
            shared_tx_cells = [cell for cell in self.mote.tsch.get_cells(None) if d.CELLOPTION_TX in cell.options]
            dedicated_tx_cells = [cell for cell in self.mote.tsch.get_cells(packet[u'mac'][u'dstMac']) if d.CELLOPTION_TX in cell.options]
            if (
                    (len(shared_tx_cells) == 0)
                    and
                    (len(dedicated_tx_cells) == 0)
                ):
                # I don't have any cell to transmit on

                # drop
                self.mote.drop_packet(
                    packet  = packet,
                    reason  = SimEngine.SimLog.DROPREASON_NO_TX_CELLS,
                )

                # couldn't enqueue
                goOn = False

        # if I get here, everyting is OK, I can enqueue
        if goOn:
            # set retriesLeft which should be renewed at every hop
            packet[u'mac'][u'retriesLeft'] = self.max_tx_retries
            # put the seqnum
            packet[u'mac'][u'seqnum'] = self.next_seqnum
            self.next_seqnum += 1
            if self.next_seqnum > 255:
                # sequence number field is 8-bit long
                self.next_seqnum = 0
            if priority:
                # mark priority to this packet
                packet[u'mac'][u'priority'] = True
                # if the queue is full, we need to drop the last one
                # in the queue or the new packet
                if len(self.txQueue) == self.txQueueSize:
                    assert not self.txQueue[-1][u'mac'][u'priority']
                    # drop the last one in the queue
                    packet_index_to_drop = self.droppable_normal_packet_index
                    packet_to_drop = self.dequeue_by_index(packet_index_to_drop)
                    self.mote.drop_packet(
                        packet = packet_to_drop,
                        reason  = SimEngine.SimLog.DROPREASON_TXQUEUE_FULL
                    )
                index = len(self.txQueue)
                for i, _ in enumerate(self.txQueue):
                    if self.txQueue[i][u'mac'][u'priority'] is False:
                        index = i
                        break
                self.txQueue.insert(index, packet)
            else:
                packet[u'mac'][u'priority'] = False
                # add to txQueue
                self.txQueue    += [packet]

        if (
                goOn
                and
                packet[u'mac'][u'dstMac'] != d.BROADCAST_ADDRESS
                and
                isinstance(self.mote.sf, SchedulingFunctionMSF)
                and
                not self.mote.sf.get_tx_cells(packet[u'mac'][u'dstMac'])
            ):
            # on-demand allocation of autonomous TX cell
            self.mote.sf.allocate_autonomous_tx_cell(
                packet[u'mac'][u'dstMac']
            )

        return goOn

    def dequeue(self, packet):
        if packet in self.txQueue:
            self.txQueue.remove(packet)
        else:
            # do nothing
            pass

        if (
                packet[u'mac'][u'dstMac'] != d.BROADCAST_ADDRESS
                and
                isinstance(self.mote.sf, SchedulingFunctionMSF)
                and
                not [
                    _pkt for _pkt in self.txQueue
                    if _pkt[u'mac'][u'dstMac'] == packet[u'mac'][u'dstMac']
                ]
                and
                self.mote.sf.get_autonomous_tx_cell(packet[u'mac'][u'dstMac'])
            ):
            # on-demand deallocation of autonomous TX cell
            self.mote.sf.deallocate_autonomous_tx_cell(
                packet[u'mac'][u'dstMac']
            )

    def dequeue_by_index(self, index):
        assert index < len(self.txQueue)
        return self.txQueue.pop(index)

    def get_first_packet_to_send(self, cell):
        assert cell
        dst_mac_addr = cell.mac_addr
        packet_to_send = None
        if dst_mac_addr is None:
            if (
                    len(self.txQueue) == 0
                    and
                    cell.link_type in [
                        d.LINKTYPE_ADVERTISING,
                        d.LINKTYPE_ADVERTISING_ONLY
                    ]
                ):
                # txQueue is empty; we may return an EB
                if (
                        self.mote.clear_to_send_EBs_DATA()
                        and
                        self._decided_to_send_eb()
                    ):
                    packet_to_send = self._create_EB()
                else:
                    packet_to_send = None
            else:
                # return the first one in the TX queue, whose destination MAC
                # is not associated with any of allocated (dedicated) TX cells
                for packet in self.txQueue:
                    packet_to_send = packet # tentatively
                    for _, slotframe in list(self.slotframes.items()):
                        dedicated_tx_cells = [cell for cell in slotframe.get_cells_by_mac_addr(packet[u'mac'][u'dstMac']) if d.CELLOPTION_TX in cell.options]
                        if len(dedicated_tx_cells) > 0:
                            packet_to_send = None
                            break # try the next packet in TX queue

                    if packet_to_send is not None:
                        # found a good packet to send
                        break

                # if no suitable packet is found, packet_to_send remains None
        else:
            for packet in self.txQueue:
                if packet[u'mac'][u'dstMac'] == dst_mac_addr:
                    # return the first one having the dstMac
                    packet_to_send = packet
                    break
            # if no packet is found, packet_to_send remains None

        return packet_to_send

    def get_num_packet_in_tx_queue(self, dst_mac_addr=None):
        if dst_mac_addr is None:
            return len(self.txQueue)
        else:
            return len(
                [
                    pkt for pkt in self.txQueue if (
                        pkt[u'mac'][u'dstMac'] == dst_mac_addr
                    )
                ]
            )

    def remove_packets_in_tx_queue(self, type, dstMac=None):
        i = 0
        while i < len(self.txQueue):
            if (
                    (self.txQueue[i][u'type'] == type)
                    and
                    (
                        (dstMac is None)
                        or
                        (self.txQueue[i][u'mac'][u'dstMac'] == dstMac)
                    )
                ):
                del self.txQueue[i]
            else:
                i += 1

    # interface with radio

    def txDone(self, isACKed, channel):
        assert isACKed in [True,False]

        asn         = self.engine.getAsn()
        active_cell = self.active_cell

        self.active_cell = None

        assert self.waitingFor == d.WAITING_FOR_TX

        # log
        self.log(
            SimEngine.SimLog.LOG_TSCH_TXDONE,
            {
                u'_mote_id':       self.mote.id,
                u'channel':        channel,
                u'slot_offset':    (
                    active_cell.slot_offset
                    if active_cell else None
                ),
                u'channel_offset': (
                    active_cell.channel_offset
                    if active_cell else None
                ),
                u'packet':         self.pktToSend,
                u'isACKed':        isACKed,
            }
        )

        if self.pktToSend[u'mac'][u'dstMac'] == d.BROADCAST_ADDRESS:
            # I just sent a broadcast packet

            assert self.pktToSend[u'type'] in [
                d.PKT_TYPE_EB,
                d.PKT_TYPE_DIO,
                d.PKT_TYPE_DIS
            ]
            assert isACKed == False

            # EBs are never in txQueue, no need to remove.
            if self.pktToSend[u'type'] != d.PKT_TYPE_EB:
                self.dequeue(self.pktToSend)

        else:
            # I just sent a unicast packet...

            # TODO send txDone up; need a more general way
            if (
                    (isACKed is True)
                    and
                    (self.pktToSend[u'type'] == d.PKT_TYPE_SIXP)
                ):
                self.mote.sixp.recv_mac_ack(self.pktToSend)

            if active_cell:
                self.mote.rpl.indicate_tx(
                    active_cell,
                    self.pktToSend[u'mac'][u'dstMac'],
                    isACKed
                )

                # update the backoff exponent
                self._update_backoff_state(
                    isRetransmission = self._is_retransmission(self.pktToSend),
                    isSharedLink     = d.CELLOPTION_SHARED in active_cell.options,
                    isTXSuccess      = isACKed,
                    packet           = self.pktToSend
                )

            if isACKed:
                # ... which was ACKed

                # update schedule stats
                if active_cell:
                    active_cell.increment_num_tx_ack()

                # time correction
                if self.clock.source == self.pktToSend[u'mac'][u'dstMac']:
                    self.asnLastSync = asn # ACK-based sync
                    self.clock.sync()
                    self._reset_keep_alive_timer()
                    self._reset_synchronization_timer()

                # remove packet from queue
                self.dequeue(self.pktToSend)

                # process the pending bit field
                if (
                        (self.pktToSend[u'mac'][u'pending_bit'] is True)
                        and
                        self._is_next_slot_unused()
                    ):
                    self._schedule_next_tx_for_pending_bit(
                        self.pktToSend[u'mac'][u'dstMac'],
                        channel
                    )
                else:
                    self.args_for_next_pending_bit_task = None

            else:
                # ... which was NOT ACKed

                # decrement 'retriesLeft' counter associated with that packet
                assert self.pktToSend[u'mac'][u'retriesLeft'] >= 0
                self.pktToSend[u'mac'][u'retriesLeft'] -= 1

                # drop packet if retried too many time
                if self.pktToSend[u'mac'][u'retriesLeft'] < 0:

                    # remove packet from queue
                    self.dequeue(self.pktToSend)

                    # drop
                    self.mote.drop_packet(
                        packet = self.pktToSend,
                        reason = SimEngine.SimLog.DROPREASON_MAX_RETRIES,
                    )

        # notify upper layers
        if active_cell:
            assert active_cell.is_tx_on()
            self.mote.sf.indication_tx_cell_elapsed(
                cell        = active_cell,
                sent_packet = self.pktToSend
            )

        # end of radio activity, not waiting for anything
        self.waitingFor = None
        self.pktToSend  = None

    def rxDone(self, packet, channel):

        # local variables
        asn         = self.engine.getAsn()
        active_cell = self.active_cell

        self.active_cell = None

        # copy the received packet to a new packet instance since the passed
        # "packet" should be kept as it is so that Connectivity can use it
        # after this rxDone() process.
        new_packet = copy.deepcopy(packet)
        packet = new_packet

        # make sure I'm in the right state
        assert self.waitingFor == d.WAITING_FOR_RX

        # not waiting for anything anymore
        self.waitingFor = None

        if packet:
            # add the source mote to the neighbor list if it's not listed yet
            if packet[u'mac'][u'srcMac'] not in self.neighbor_table:
                self.neighbor_table.append(packet[u'mac'][u'srcMac'])

            # accept only EBs while we're not syncrhonized
            if (
                    (self.getIsSync() is False)
                    and
                    (packet[u'type'] != d.PKT_TYPE_EB)
                ):
                return False # isACKed

            # abort if I received a frame for someone else
            if (
                    (packet[u'mac'][u'dstMac'] != d.BROADCAST_ADDRESS)
                    and
                    (self.mote.is_my_mac_addr(packet[u'mac'][u'dstMac']) is False)
                ):
                return False # isACKed

            # if I get here, I received a frame at the link layer (either unicast for me, or broadcast)

            # log
            self.log(
                SimEngine.SimLog.LOG_TSCH_RXDONE,
                {
                    u'_mote_id':       self.mote.id,
                    u'channel':        channel,
                    u'slot_offset':    (
                        active_cell.slot_offset
                        if active_cell else None
                    ),
                    u'channel_offset': (
                        active_cell.channel_offset
                        if active_cell else None
                    ),
                    u'packet':         packet,
                }
            )

            # time correction
            if self.clock.source == packet[u'mac'][u'srcMac']:
                self.asnLastSync = asn # packet-based sync
                self.clock.sync()
                self._reset_keep_alive_timer()
                self._reset_synchronization_timer()

            # update schedule stats
            if (
                    self.getIsSync()
                    and
                    active_cell
                ):
                    active_cell.increment_num_rx()

            if   self.mote.is_my_mac_addr(packet[u'mac'][u'dstMac']):
                # link-layer unicast to me

                # ACK frame
                isACKed = True

                # save the pending bit here since the packet instance may be made
                # empty by an upper layer process
                is_pending_bit_on = packet[u'mac'][u'pending_bit']

                # dispatch to the right upper layer
                if   packet[u'type'] == d.PKT_TYPE_SIXP:
                    self.mote.sixp.recv_packet(packet)
                elif packet[u'type'] == d.PKT_TYPE_KEEP_ALIVE:
                    # do nothing but send back an ACK
                    pass
                elif u'net' in packet:
                    self.mote.sixlowpan.recvPacket(packet)
                else:
                    raise SystemError()

                if (
                        is_pending_bit_on
                        and
                        self._is_next_slot_unused()
                    ):
                    self._schedule_next_rx_by_pending_bit(channel)

            elif packet[u'mac'][u'dstMac'] == d.BROADCAST_ADDRESS:
                # link-layer broadcast

                # do NOT ACK frame (broadcast)
                isACKed = False

                # dispatch to the right upper layer
                if   packet[u'type'] == d.PKT_TYPE_EB:
                    self._action_receiveEB(packet)
                elif u'net' in packet:
                    assert packet[u'type'] in [
                        d.PKT_TYPE_DIO,
                        d.PKT_TYPE_DIS
                    ]
                    self.mote.sixlowpan.recvPacket(packet)
                else:
                    raise SystemError()

            else:
                raise SystemError()
        else:
            # received nothing (idle listen)
            isACKed = False

        # notify upper layers
        if active_cell:
            assert active_cell.is_rx_on()
            self.mote.sf.indication_rx_cell_elapsed(
                cell            = active_cell,
                received_packet = packet
            )

        return isACKed

    #======================== private ==========================================

    # listeningForEB

    def _action_listeningForEB_cell(self):
        """
        active slot starts, while mote is listening for EBs
        """

        assert not self.getIsSync()

        # choose random channel
        channel = random.choice(self.hopping_sequence)

        # start listening
        self.mote.radio.startRx(channel)

        # indicate that we're waiting for the RX operation to finish
        self.waitingFor = d.WAITING_FOR_RX

        # schedule next listeningForEB cell
        self.schedule_next_listeningForEB_cell()

    def _perform_synchronization(self):
        if not self.received_eb_list:
            # this method call should be in a timer task and we should
            # have already been synchronized at the same ASN
            assert self.isSync
            return

        # [Section 6.3.6, IEEE802.15.4-2015]
        # The higher layer may wait for additional
        # MLME-BEACON-NOTIFY.indication primitives before selecting a
        # TSCH network based upon the value of the Join Metric field
        # in the TSCH Synchronization IE. (snip)
        #
        # NOTE- lower value in the Join Metric field indicates that
        # connection of the beaconing device to a specific network
        # device determined by the higher layer is a shorter route.
        clock_source_mac_addr = min(
            self.received_eb_list,
            key=lambda x: self.received_eb_list[x][u'mac'][u'join_metric']
        )
        clock_source = self.engine.get_mote_by_mac_addr(clock_source_mac_addr)
        if clock_source.dagRoot or clock_source.tsch.getIsSync():
            self.clock.sync(clock_source_mac_addr)
            self.setIsSync(True) # mote

            # the mote that sent the EB is now by join proxy
            self.join_proxy = netaddr.EUI(clock_source_mac_addr)

            # add the minimal cell to the schedule (read from EB)
            self.add_minimal_cell() # mote

            # trigger join process
            self.mote.secjoin.startJoinProcess()
        else:
            # our clock source is desynchronized; we cannot get
            # synchronized with the network using the source
            pass

        # clear the EB list
        self.received_eb_list = {}

    # active cell

    def _select_active_cell(self, candidate_cells):
        active_cell = None
        packet_to_send = None

        for cell in candidate_cells:
            if cell.is_tx_on():
                if (
                        (packet_to_send is None)
                        or
                        (
                            self.get_num_packet_in_tx_queue(packet_to_send[u'mac'][u'dstMac'])
                            <
                            self.get_num_packet_in_tx_queue(cell.mac_addr)
                        )
                    ):
                    # try to find a packet to send
                    _packet_to_send = self.get_first_packet_to_send(cell)

                    # take care of the retransmission backoff algorithm
                    if _packet_to_send is not None:
                        if _packet_to_send[u'type'] == d.PKT_TYPE_EB:
                            if (
                                    (
                                        (cell.mac_addr is None)
                                        or
                                        (cell.mac_addr == d.BROADCAST_ADDRESS)
                                    )
                                    and
                                    (
                                        cell.link_type in
                                        [
                                            d.LINKTYPE_ADVERTISING,
                                            d.LINKTYPE_ADVERTISING_ONLY
                                        ]
                                    )
                                ):
                                # we can send the EB on this link (cell)
                                packet_to_send = _packet_to_send
                                active_cell = cell
                            else:
                                # we don't send an EB on a NORMAL
                                # link; skip this one
                                pass
                        elif (
                            cell.is_shared_on()
                            and
                            self._is_retransmission(_packet_to_send)
                            and
                            (u'backoff_remaining_delay' in _packet_to_send)
                            and
                            (_packet_to_send[u'backoff_remaining_delay'] > 0)
                        ):
                            _packet_to_send[u'backoff_remaining_delay'] -= 1
                            # skip this cell for transmission
                        else:
                            packet_to_send = _packet_to_send
                            active_cell = cell

            if (
                    cell.is_rx_on()
                    and
                    (packet_to_send is None)
                ):
                active_cell = cell

        if (
                (packet_to_send is not None)
                and
                (u'backoff_remaining_delay' in packet_to_send)
            ):
            del packet_to_send[u'backoff_remaining_delay']
        return active_cell, packet_to_send

    def _schedule_next_active_slot(self):

        assert self.getIsSync()

        asn       = self.engine.getAsn()
        tsCurrent = asn % self.settings.tsch_slotframeLength

        # find closest active slot in schedule

        if not self.isSync:
            self.engine.removeFutureEvent(uniqueTag=(self.mote.id, u'_action_active_cell'))
            return

        try:
            tsDiffMin = min(
                [
                    slotframe.get_num_slots_to_next_active_cell(asn)
                    for _, slotframe in list(self.slotframes.items()) if (
                        len(slotframe.get_busy_slots()) > 0
                    )
                ]
            )
        except ValueError:
            # we don't have any cell; return without scheduling the next active
            # slot
            return

        # schedule at that ASN
        self.engine.scheduleAtAsn(
            asn            = asn+tsDiffMin,
            cb             = self._action_active_cell,
            uniqueTag      = (self.mote.id, u'_action_active_cell'),
            intraSlotOrder = d.INTRASLOTORDER_STARTSLOT,
        )

    def _action_active_cell(self):
        # cancel a task for the pending bit if scheduled on the same slot
        self.args_for_next_pending_bit_task = None

        # local shorthands
        asn = self.engine.getAsn()

        # make sure we're not in the middle of a TX/RX operation
        assert self.waitingFor == None
        # make sure we are not busy sending a packet
        assert self.pktToSend == None

        # section 6.2.6.4 of IEEE 802.15.4-2015:
        # "When, for any given timeslot, a device has links in multiple
        # slotframes, transmissions take precedence over receives, and lower
        # macSlotframeHandle slotframes takes precedence over higher
        # macSlotframeHandle slotframes."

        candidate_cells = []
        for _, slotframe in list(self.slotframes.items()):
            candidate_cells = slotframe.get_cells_at_asn(asn)
            if len(candidate_cells) > 0:
                break

        if len(candidate_cells) == 0:
            # we don't have any cell at this asn. we may have used to have
            # some, which possibly were removed; do nothing
            pass
        else:
            # identify a cell to be activated
            self.active_cell, self.pktToSend = self._select_active_cell(candidate_cells)

        if self.active_cell:
            if self.pktToSend is None:
                assert self.active_cell.is_rx_on()
                self._action_RX()
            else:
                assert self.active_cell.is_tx_on()
                self._action_TX(
                    pktToSend = self.pktToSend,
                    channel   = self._get_physical_channel(self.active_cell)
                )
                # update cell stats
                self.active_cell.increment_num_tx()
                if self.pktToSend[u'mac'][u'dstMac'] == self.clock.source:
                    # we're going to send a frame to our time source; reset the
                    # keep-alive timer
                    self._reset_keep_alive_timer()
        else:
            # do nothing
            pass

        # notify upper layers
        for cell in candidate_cells:
            # call methods against unselected (non-active) cells
            if cell != self.active_cell:
                if cell.is_tx_on():
                    self.mote.sf.indication_tx_cell_elapsed(
                        cell        = cell,
                        sent_packet = None
                    )
                if cell.is_rx_on():
                    self.mote.sf.indication_rx_cell_elapsed(
                        cell            = cell,
                        received_packet = None
                    )
        # schedule the next active slot
        self._schedule_next_active_slot()

    def _action_TX(self, pktToSend, channel):
        # set the pending bit field
        if (
                (pktToSend[u'mac'][u'dstMac'] != d.BROADCAST_ADDRESS)
                and
                (
                    # we have more than one packet destined to the same
                    # neighbor
                    len(
                        [
                            packet for packet in self.txQueue
                            if (
                                packet[u'mac'][u'dstMac'] ==
                                pktToSend[u'mac'][u'dstMac']
                            )
                        ]
                    ) > 1
                )
                and
                self._is_next_slot_unused()
                and
                self.pending_bit_enabled
            ):
            pktToSend[u'mac'][u'pending_bit'] = True
        else:
            pktToSend[u'mac'][u'pending_bit'] = False

        # send packet to the radio
        self.mote.radio.startTx(channel, pktToSend)

        # indicate that we're waiting for the TX operation to finish
        self.waitingFor = d.WAITING_FOR_TX

    def _action_RX(self):

        # start listening
        self.mote.radio.startRx(
            channel = self._get_physical_channel(self.active_cell)
        )

        # indicate that we're waiting for the RX operation to finish
        self.waitingFor = d.WAITING_FOR_RX

    def _get_physical_channel(self, cell):
        # see section 6.2.6.3 of IEEE 802.15.4-2015
        return self.hopping_sequence[
            (self.engine.getAsn() + cell.channel_offset) %
            len(self.hopping_sequence)
        ]

    # EBs

    def _decided_to_send_eb(self):
        # short-hand
        prob = float(self.settings.tsch_probBcast_ebProb)
        n    = 1 + len(self.neighbor_table)

        # following the Bayesian broadcasting algorithm
        return (
            (random.random() < (old_div(prob, n)))
            and
            self.iAmSendingEBs
        )

    def _create_EB(self):

        join_metric = self.mote.rpl.getDagRank()
        if join_metric is None:
            newEB = None
        else:
            # create
            newEB = {
                u'type':            d.PKT_TYPE_EB,
                u'mac': {
                    u'srcMac':      self.mote.get_mac_addr(),
                    u'dstMac':      d.BROADCAST_ADDRESS,     # broadcast
                    u'join_metric': self.mote.rpl.getDagRank() - 1
                }
            }

            # log
            self.log(
                SimEngine.SimLog.LOG_TSCH_EB_TX,
                {
                    u'_mote_id': self.mote.id,
                    u'packet':   newEB,
                }
            )

        return newEB

    def _action_receiveEB(self, packet):

        assert packet[u'type'] == d.PKT_TYPE_EB

        # log
        self.log(
            SimEngine.SimLog.LOG_TSCH_EB_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet':   packet,
            }
        )

        # abort if I'm the root
        if self.mote.dagRoot:
            return

        if not self.getIsSync():
            event_tag = (self.mote.id, u'tsch', u'wait_eb')
            if not self.received_eb_list:
                # start the timer to wait for other EBs if this is the
                # first received EB
                self.engine.scheduleIn(
                    delay          = d.TSCH_MAX_EB_DELAY,
                    cb             = self._perform_synchronization,
                    uniqueTag      = event_tag,
                    intraSlotOrder = d.INTRASLOTORDER_STACKTASKS
                )
            # add the EB to the list. If there is an EB from the
            # the source, the EB is replaced by the new one
            self.received_eb_list[packet[u'mac'][u'srcMac']] = packet
            # receiving EB while not sync'ed
            if len(self.received_eb_list) == d.TSCH_NUM_NEIGHBORS_TO_WAIT:
                self._perform_synchronization()
                self.engine.removeFutureEvent(event_tag)
            else:
                assert len(self.received_eb_list) < d.TSCH_NUM_NEIGHBORS_TO_WAIT

    # Retransmission backoff algorithm
    def _is_retransmission(self, packet):
        assert packet is not None
        if u'retriesLeft' not in packet[u'mac']:
            assert packet[u'mac'][u'dstMac'] == d.BROADCAST_ADDRESS
            return False
        else:
            return (
                packet[u'mac'][u'retriesLeft'] < self.max_tx_retries
            )

    def _decide_backoff_delay(self):
        # Section 6.2.5.3 of IEEE 802.15.4-2015: "The MAC sublayer shall delay
        # for a random number in the range 0 to (2**BE - 1) shared links (on
        # any slotframe) before attempting a retransmission on a shared link."
        return random.randint(0, pow(2, self.backoff_exponent) - 1)

    def _reset_backoff_state(self):
        old_be = self.backoff_exponent
        self.backoff_exponent = d.TSCH_MIN_BACKOFF_EXPONENT
        self.log(
            SimEngine.SimLog.LOG_TSCH_BACKOFF_EXPONENT_UPDATED,
            {
                u'_mote_id': self.mote.id,
                u'old_be'  : old_be,
                u'new_be'  : self.backoff_exponent
            }
        )

    def _increase_backoff_exponent(self):
        old_be = self.backoff_exponent
        # In Figure 6-6 of IEEE 802.15.4, BE (backoff exponent) is updated as
        # "BE - min(BE 0 1, macMinBe)". However, it must be incorrect. The
        # right formula should be "BE = min(BE + 1, macMaxBe)", that we apply
        # here.
        self.backoff_exponent = min(
            self.backoff_exponent + 1,
            d.TSCH_MAX_BACKOFF_EXPONENT
        )
        self.log(
            SimEngine.SimLog.LOG_TSCH_BACKOFF_EXPONENT_UPDATED,
            {
                u'_mote_id': self.mote.id,
                u'old_be'  : old_be,
                u'new_be'  : self.backoff_exponent
            }
        )

    def _update_backoff_state(
            self,
            isRetransmission,
            isSharedLink,
            isTXSuccess,
            packet
        ):
        if isSharedLink:
            if isTXSuccess:
                # Section 6.2.5.3 of IEEE 802.15.4-2015: "A successful
                # transmission in a shared link resets the backoff window to
                # the minimum value."
                self._reset_backoff_state()
            else:
                if isRetransmission:
                    # Section 6.2.5.3 of IEEE 802.15.4-2015: "The backoff window
                    # increases for each consecutive failed transmission in a
                    # shared link."
                    self._increase_backoff_exponent()
                else:
                    # First attempt to transmit the packet
                    #
                    # Section 6.2.5.3 of IEEE 802.15.4-2015: "A device upon
                    # encountering a transmission failure in a shared link
                    # shall initialize the BE to macMinBe."
                    self._reset_backoff_state()
                packet[u'backoff_remaining_delay'] = self._decide_backoff_delay()

        else:
            # dedicated link (which is different from a dedicated *cell*)
            if isTXSuccess:
                # successful transmission
                if len(self.txQueue) == 0:
                    # Section 6.2.5.3 of IEEE 802.15.4-2015: "The backoff
                    # window is reset to the minimum value if the transmission
                    # in a dedicated link is successful and the transmit queue
                    # is then empty."
                    self._reset_backoff_state()
                else:
                    # Section 6.2.5.3 of IEEE 802.15.4-2015: "The backoff
                    # window does not change when a transmission is successful
                    # in a dedicated link and the transmission queue is still
                    # not empty afterwards."
                    pass
            else:
                # Section 6.2.5.3 of IEEE 802.15.4-2015: "The backoff window
                # does not change when a transmission is a failure in a
                # dedicated link."
                pass

    # Synchronization / Keep-Alive
    def _send_keep_alive_message(self):
        if self.clock.source is None:
            return

        if (
                (len(self.txQueue) > 0)
                and
                (self.txQueue[0][u'mac'][u'dstMac'] == self.clock.source)
            ):
            # don't send a keep-alive packet if the first packet in the TX
            # queue has the MAC address of the preferred parent (clock source)
            # as its destination address
            return

        packet = {
            u'type': d.PKT_TYPE_KEEP_ALIVE,
            u'mac': {
                u'srcMac': self.mote.get_mac_addr(),
                u'dstMac': self.clock.source
            }
        }
        self.enqueue(packet, priority=True)
        # the next keep-alive event will be scheduled on receiving an ACK

    def _start_keep_alive_timer(self):
        assert self.settings.tsch_keep_alive_interval >= 0
        if (
                (self.settings.tsch_keep_alive_interval == 0)
                or
                (self.mote.dagRoot is True)
            ):
            # do nothing
            pass
        else:
            # the clock drift of the child against the parent should be less
            # than macTsRxWait/2 so that they can communicate with each
            # other. Their clocks can be off by one clock interval at the
            # most. This means, the clock difference between the child and the
            # parent could be clock_interval just after synchronization. then,
            # the possible minimum guard time is ((macTsRxWait / 2) -
            # clock_interval). When macTsRxWait is 2,200 usec and
            # clock_interval is 30 usec, the minimum guard time is 1,070
            # usec. they will be desynchronized without keep-alive in 16
            # seconds as the paper titled "Adaptive Synchronization in
            # IEEE802.15.4e Networks" describes.
            #
            # the keep-alive interval should be configured in config.json with
            # "tsch_keep_alive_interval".
            self.engine.scheduleIn(
                delay          = self.settings.tsch_keep_alive_interval,
                cb             = self._send_keep_alive_message,
                uniqueTag      = self._get_event_tag(u'tsch.keep_alive_event'),
                intraSlotOrder = d.INTRASLOTORDER_STACKTASKS
            )

    def _stop_keep_alive_timer(self):
        self.engine.removeFutureEvent(
            uniqueTag = self._get_event_tag(u'tsch.keep_alive_event')
        )

    def _reset_keep_alive_timer(self):
        self._stop_keep_alive_timer()
        self._start_keep_alive_timer()

    def _start_synchronization_timer(self):
        self._reset_synchronization_timer()

    def _stop_synchronization_timer(self):
        self.engine.removeFutureEvent(
            uniqueTag = self._get_event_tag(u'tsch.synchronization_timer')
        )

    def _reset_synchronization_timer(self):
        if (
                (self.settings.tsch_keep_alive_interval == 0)
                or
                (self.mote.dagRoot is True)
            ):
            # do nothing
            pass
        else:
            target_asn = self.engine.getAsn() + d.TSCH_DESYNCHRONIZED_TIMEOUT_SLOTS

            def _desync():
                self.setIsSync(False)

            self.engine.scheduleAtAsn(
                asn            = target_asn,
                cb             = _desync,
                uniqueTag      = self._get_event_tag(u'tsch.synchronization_timer'),
                intraSlotOrder = d.INTRASLOTORDER_STACKTASKS
            )

    def _get_event_tag(self, event_name):
        return u'{0}-{1}'.format(self.mote.id, event_name)

    def _get_synchronization_event_tag(self):
        return u'{0}-{1}.format()'

    # Pending bit
    def _schedule_next_tx_for_pending_bit(self, dstMac, channel):
        self.args_for_next_pending_bit_task = {
            u'dstMac' : dstMac,
            u'channel': channel
        }
        self.engine.scheduleAtAsn(
            asn            = self.engine.getAsn() + 1,
            cb             = self._action_tx_for_pending_bit,
            uniqueTag      = (self.mote.id, u'_action_tx_for_pending_bit'),
            intraSlotOrder = d.INTRASLOTORDER_STARTSLOT,
        )

    def _schedule_next_rx_by_pending_bit(self, channel):
        self.args_for_next_pending_bit_task = {
            u'channel': channel
        }
        self.engine.scheduleAtAsn(
            asn            = self.engine.getAsn() + 1,
            cb             = self._action_rx_for_pending_bit,
            uniqueTag      = (self.mote.id, u'_action_rx_for_pending_bit'),
            intraSlotOrder = d.INTRASLOTORDER_STARTSLOT,
        )

    def _action_tx_for_pending_bit(self):
        if self.args_for_next_pending_bit_task is None:
            # it seems this TX was canceled by an active cell scheduled on the
            # same slot
            return

        assert self.waitingFor == None
        assert self.pktToSend == None

        for packet in self.txQueue:
            if (
                    packet[u'mac'][u'dstMac'] ==
                    self.args_for_next_pending_bit_task[u'dstMac']
                ):
                self.pktToSend = packet
                break

        if self.pktToSend is None:
            # done
            return
        else:
            # self.args_for_next_pending_bit_task will be updated in the TX
            # operation
            self._action_TX(
                pktToSend = self.pktToSend,
                channel   = self.args_for_next_pending_bit_task[u'channel']
            )

    def _action_rx_for_pending_bit(self):
        if self.args_for_next_pending_bit_task is None:
            # it seems this RX was canceled by an active cell scheduled on the
            # same slot
            return

        # self.args_for_next_pending_bit_task will be updated in the RX
        # operation
        self.mote.radio.startRx(
            self.args_for_next_pending_bit_task[u'channel']
        )
        self.waitingFor = d.WAITING_FOR_RX

    def _is_next_slot_unused(self):
        ret_val = True
        for slotframe in list(self.slotframes.values()):
            next_slot = (self.engine.getAsn() + 1) % slotframe.length
            cells_on_next_slot = slotframe.get_cells_by_slot_offset(next_slot)
            if len(cells_on_next_slot) > 0:
                ret_val = False
                break

        return ret_val


class Clock(object):
    def __init__(self, mote):
        # singleton
        self.engine   = SimEngine.SimEngine.SimEngine()
        self.settings = SimEngine.SimSettings.SimSettings()

        # local variables
        self.mote = mote

        # instance variables which can be accessed directly from outside
        self.source = None

        # private variables
        self._clock_interval = 1.0 / self.settings.tsch_clock_frequency
        self._error_rate     = self._initialize_error_rate()

        self.desync()

    @staticmethod
    def get_clock_by_mac_addr(mac_addr):
        engine = SimEngine.SimEngine.SimEngine()
        mote = engine.get_mote_by_mac_addr(mac_addr)
        return mote.tsch.clock

    def desync(self):
        self.source             = None
        self._clock_off_on_sync = 0
        self._accumulated_error = 0
        self._last_clock_access = None

    def sync(self, clock_source=None):
        if self.mote.dagRoot is True:
            # if you're the DAGRoot, you should have the perfect clock from the
            # point of view of the network.
            self._clock_off_on_sync = 0
        else:
            if clock_source is None:
                assert self.source is not None
            else:
                self.source = clock_source

            # the clock could be off by between 0 and 30 usec (clock interval)
            # from the clock source when 32.768 Hz oscillators are used on the
            # both sides. in addition, the clock source also off from a certain
            # amount of time from its source.
            off_from_source = random.random() * self._clock_interval
            source_clock = self.get_clock_by_mac_addr(self.source)
            self._clock_off_on_sync = off_from_source + source_clock.get_drift()

        self._accumulated_error = 0
        self._last_clock_access = self.engine.getAsn()

    def get_drift(self):
        if self.mote.dagRoot is True:
            # if we're the DAGRoot, we are the clock source of the entire
            # network. our clock never drifts from itself. Its clock drift is
            # taken into accout by motes who use our clock as their reference
            # clock.
            error = 0
        elif self._last_clock_access:
            assert self._last_clock_access <= self.engine.getAsn()
            slot_duration = self.engine.settings.tsch_slotDuration
            elapsed_slots = self.engine.getAsn() - self._last_clock_access
            elapsed_time  = elapsed_slots * slot_duration
            error = elapsed_time * self._error_rate
        else:
            # self._last_clock_access is None; we're desynchronized.
            # in this case, we will return 0 as drift, although there
            # should be a better thing to do.
            error = None

        if error:
            # update the variables
            self._accumulated_error += error
            self._last_clock_access = self.engine.getAsn()

            # return the result
            return self._clock_off_on_sync + self._accumulated_error
        else:
            return 0

    def _initialize_error_rate(self):
        # private variables:
        # the clock drifts by its error rate. for simplicity, we double the
        # error rate to express clock drift from the time source. That is,
        # our clock could drift by 30 ppm at the most and the clock of time
        # source also could drift as well ppm. Then, our clock could drift
        # by 60 ppm from the clock of the time source.
        #
        # we assume the error rate is constant over the simulation time.
        max_drift = (
            float(self.settings.tsch_clock_max_drift_ppm) / pow(10, 6)
        )
        return random.uniform(-1 * max_drift * 2, max_drift * 2)


class SlotFrame(object):
    def __init__(self, mote_id, slotframe_handle, num_slots):
        self.log = SimEngine.SimLog.SimLog().log

        self.mote_id = mote_id
        self.slotframe_handle = slotframe_handle
        self.length = num_slots
        self.slots  = {}
        # index by neighbor_mac_addr for quick access
        self.cells  = {}

    def __repr__(self):
        return u'slotframe(length: {0}, num_cells: {1})'.format(
            self.length,
            len(list(chain.from_iterable(list(self.slots.values()))))
        )

    def add(self, cell):
        assert cell.slot_offset < self.length
        if cell.slot_offset not in self.slots:
            self.slots[cell.slot_offset] = [cell]
        else:
            self.slots[cell.slot_offset] += [cell]

        if cell.mac_addr not in self.cells:
            self.cells[cell.mac_addr] = [cell]
        else:
            self.cells[cell.mac_addr] += [cell]
        cell.slotframe = self

        # log
        self.log(
            SimEngine.SimLog.LOG_TSCH_ADD_CELL,
            {
                u'_mote_id':        self.mote_id,
                u'slotFrameHandle': self.slotframe_handle,
                u'slotOffset':      cell.slot_offset,
                u'channelOffset':   cell.channel_offset,
                u'neighbor':        cell.mac_addr,
                u'cellOptions':     cell.options
            }
        )

    def delete(self, cell):
        assert cell.slot_offset < self.length
        assert cell in self.slots[cell.slot_offset]
        assert cell in self.cells[cell.mac_addr]
        self.slots[cell.slot_offset].remove(cell)
        self.cells[cell.mac_addr].remove(cell)
        if len(self.cells[cell.mac_addr]) == 0:
            del self.cells[cell.mac_addr]
        if len(self.slots[cell.slot_offset]) == 0:
            del self.slots[cell.slot_offset]

        # log
        self.log(
            SimEngine.SimLog.LOG_TSCH_DELETE_CELL,
            {
                u'_mote_id':        self.mote_id,
                u'slotFrameHandle': self.slotframe_handle,
                u'slotOffset':      cell.slot_offset,
                u'channelOffset':   cell.channel_offset,
                u'neighbor':        cell.mac_addr,
                u'cellOptions':     cell.options,
            }
        )

    def get_cells_by_slot_offset(self, slot_offset):
        assert slot_offset < self.length
        if slot_offset in self.slots:
            return self.slots[slot_offset]
        else:
            return []

    def get_cells_at_asn(self, asn):
        slot_offset = asn % self.length
        return self.get_cells_by_slot_offset(slot_offset)

    def get_cells_by_mac_addr(self, mac_addr):
        if mac_addr in self.cells:
            return self.cells[mac_addr][:]
        else:
            return []

    def get_busy_slots(self):
        busy_slots = list(self.slots.keys())
        # busy_slots.sort()
        return busy_slots

    def get_num_slots_to_next_active_cell(self, asn):
        diff = 1
        while diff <= self.length:
            slot_offset = (asn + diff) % self.length
            if slot_offset in self.slots:
                return diff
            diff += 1
        return None

    def get_available_slots(self):
        """
        Get the list of slot offsets that are not being used (no cell attached)
        :return: a list of slot offsets (int)
        :rtype: list
        """
        all_slots = set(range(self.length))
        return list(all_slots - set(self.get_busy_slots()))

    def get_cells_filtered(self, mac_addr="", cell_options=None):
        """
        Returns a filtered list of cells
        Filtering can be done by cell options, mac_addr or both
        :param mac_addr: the neighbor mac_addr
        :param cell_options: a list of cell options
        :rtype: list
        """

        if mac_addr == "":
            target_cells = chain.from_iterable(list(self.slots.values()))
        elif mac_addr not in self.cells:
            target_cells = []
        else:
            target_cells = self.cells[mac_addr]

        if cell_options is None:
            condition = lambda c: True
        else:
            condition = lambda c: sorted(c.options) == sorted(cell_options)

        # apply filter
        return list(filter(condition, target_cells))

    def set_length(self, new_length):
        # delete extra cells and slots if reducing slotframe length
        if new_length < self.length:
            # delete cells

            slot_offset = new_length
            while slot_offset < self.length:
                if slot_offset in self.slots:
                    for cell in self.slots[slot_offset]:
                        self.delete(cell)
                slot_offset += 1

        # apply the new length
        self.length = new_length

class Cell(object):
    def __init__(
            self,
            slot_offset,
            channel_offset,
            options,
            mac_addr=None,
            link_type=d.LINKTYPE_NORMAL
        ):

        # FIXME: is_advertising is not used effectively now

        # slot_offset and channel_offset are 16-bit values
        assert slot_offset    < 0x10000
        assert channel_offset < 0x10000

        self.slot_offset    = slot_offset
        self.channel_offset = channel_offset
        self.options        = options
        self.mac_addr       = mac_addr
        self.link_type      = link_type

        # back reference to slotframe; this will be set in SlotFrame.add()
        self.slotframe = None

        # stats
        self.num_tx     = 0
        self.num_tx_ack = 0
        self.num_rx     = 0

    def __repr__(self):

        return u'cell({0})'.format(
            u', '.join(
                [
                    u'slot_offset: {0}'.format(self.slot_offset),
                    u'channel_offset: {0}'.format(self.channel_offset),
                    u'mac_addr: {0}'.format(self.mac_addr),
                    u'options: [{0}]'.format(', '.join(self.options)),
                    u'link_type: {0}'.format(self.link_type)
                ]
            )
        )

    def __eq__(self, other):
        return str(self) == str(other)

    def increment_num_tx(self):
        self.num_tx += 1

        # Seciton 5.3 of draft-ietf-6tisch-msf-00: "When NumTx reaches 256,
        # both NumTx and NumTxAck MUST be divided by 2.  That is, for example,
        # from NumTx=256 and NumTxAck=128, they become NumTx=128 and
        # NumTxAck=64. This operation does not change the value of the PDR, but
        # allows the counters to keep incrementing.
        if self.num_tx == 256:
            self.num_tx /= 2
            self.num_tx_ack /= 2

    def increment_num_tx_ack(self):
        self.num_tx_ack += 1

    def increment_num_rx(self):
        self.num_rx += 1

    def is_tx_on(self):
        return d.CELLOPTION_TX in self.options

    def is_rx_on(self):
        return d.CELLOPTION_RX in self.options

    def is_shared_on(self):
        return d.CELLOPTION_SHARED in self.options
