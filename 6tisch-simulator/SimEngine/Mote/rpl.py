""" RPL Implementation
references:
- IETF RFC 6550
- IETF RFC 6552
- IETF RFC 6553
- IETF RFC 8180

note:
- global repair is not supported
"""
from __future__ import absolute_import
from __future__ import division

# =========================== imports =========================================

from builtins import str
from builtins import object
from past.utils import old_div
import random
import math
import sys

import netaddr
import numpy

# Mote sub-modules

# Simulator-wide modules
import SimEngine
from . import MoteDefines as d
from .trickle_timer import TrickleTimer

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

class Rpl(object):

    DEFAULT_DIO_INTERVAL_MIN = 14
    DEFAULT_DIO_INTERVAL_DOUBLINGS = 9
    DEFAULT_DIO_REDUNDANCY_CONSTANT = 3

    # locally-defined constants
    DEFAULT_DIS_INTERVAL_SECONDS = 60

    def __init__(self, mote):

        # store params
        self.mote                      = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine                    = SimEngine.SimEngine.SimEngine()
        self.settings                  = SimEngine.SimSettings.SimSettings()
        self.log                       = SimEngine.SimLog.SimLog().log

        # local variables
        self.dodagId                   = None
        self.of                        = RplOFNone(self)
        self.trickle_timer             = TrickleTimer(
            i_min    = pow(2, self.DEFAULT_DIO_INTERVAL_MIN),
            i_max    = self.DEFAULT_DIO_INTERVAL_DOUBLINGS,
            k        = self.DEFAULT_DIO_REDUNDANCY_CONSTANT,
            callback = self._send_DIO
        )
        self.parentChildfromDAOs       = {}      # dictionary containing parents of each node
        self._tx_stat                  = {}      # indexed by mote_id
        self.dis_mode = self._get_dis_mode()

    #======================== public ==========================================

    # getters/setters

    def get_rank(self):
        return self.of.rank

    def getDagRank(self):
        if self.of.rank is None:
            return None
        else:
            return int(old_div(self.of.rank, d.RPL_MINHOPRANKINCREASE))

    def addParentChildfromDAOs(self, parent_addr, child_addr):
        self.parentChildfromDAOs[child_addr] = parent_addr

    def getPreferredParent(self):
        # return the MAC address of the current preferred parent
        return self.of.get_preferred_parent()

    # admin

    def start(self):
        if self.mote.dagRoot:
            self.dodagId = self.mote.get_ipv6_global_addr()
            self.of.set_rank(d.RPL_MINHOPRANKINCREASE)
            self.trickle_timer.start()
            # now start a new RPL instance; reset the timer as per Section 8.3 of
            # RFC 6550
            self.trickle_timer.reset()
        else:
            if self.settings.rpl_of:
                # update OF with one specified in config.json
                of_class  = u'Rpl{0}'.format(self.settings.rpl_of)
                self.of = getattr(sys.modules[__name__], of_class)(self)
            if self.dis_mode != u'disabled':
                # the destination address of the first DIS is determined based
                # on self.dis_mode
                if self.dis_mode == u'dis_unicast':
                    # join_proxy is a possible parent
                    dstIp = str(self.mote.tsch.join_proxy.ipv6_link_local())
                elif self.dis_mode == u'dis_broadcast':
                    dstIp = d.IPV6_ALL_RPL_NODES_ADDRESS
                else:
                    raise NotImplementedError()
                self.send_DIS(dstIp)
                self.start_dis_timer()

    def stop(self):
        assert not self.mote.dagRoot
        self.dodagId = None
        self.trickle_timer.stop()
        self.stop_dis_timer()

    def indicate_tx(self, cell, dstMac, isACKed):
        self.of.update_etx(cell, dstMac, isACKed)

    def indicate_preferred_parent_change(self, old_preferred, new_preferred):
        # log
        self.log(
            SimEngine.SimLog.LOG_RPL_CHURN,
            {
                "_mote_id":        self.mote.id,
                "rank":            self.of.rank,
                "preferredParent": new_preferred
            }
        )

        if new_preferred is None:
            assert old_preferred
            # stop the DAO timer
            self._stop_sendDAO()

            # don't change the clock source

            # trigger a DIO which advertises infinite rank
            self._send_DIO()

            # stop the trickle timer
            self.trickle_timer.stop()

            # stop the EB transmission
            self.mote.tsch.stopSendingEBs()

            # start the DIS timer
            self.start_dis_timer()
        else:
            # trigger DAO
            self._schedule_sendDAO(firstDAO=True)

            # use the new parent as our clock source
            self.mote.tsch.clock.sync(new_preferred)

            # reset trickle timer to inform new rank quickly
            self.trickle_timer.reset()

        # trigger 6P ADD if parent changed
        self.mote.sf.indication_parent_change(old_preferred, new_preferred)

    def local_repair(self):
        self.of.reset()
        assert (
            (self.of.rank is None)
            or
            (self.of.rank == d.RPL_INFINITE_RANK)
        )
        self.log(
            SimEngine.SimLog.LOG_RPL_LOCAL_REPAIR,
            {
                "_mote_id":        self.mote.id
            }
        )
        self.dodagId = None

    # === DIS

    def action_receiveDIS(self, packet):
        self.log(
            SimEngine.SimLog.LOG_RPL_DIS_RX,
            {
                "_mote_id":  self.mote.id,
                "packet":    packet,
            }
        )
        if self.dodagId is None:
            # ignore DIS
            pass
        else:
            if   self.mote.is_my_ipv6_addr(packet[u'net'][u'dstIp']):
                # unicast DIS; send unicast DIO back to the source
                self._send_DIO(packet[u'net'][u'srcIp'])
            elif packet[u'net'][u'dstIp'] == d.IPV6_ALL_RPL_NODES_ADDRESS:
                # broadcast DIS
                self.trickle_timer.reset()
            else:
                # shouldn't happen
                assert False

    def _get_dis_mode(self):
        if   u'dis_unicast' in self.settings.rpl_extensions:
            assert u'dis_broadcast' not in self.settings.rpl_extensions
            return u'dis_unicast'
        elif 'dis_broadcast' in self.settings.rpl_extensions:
            assert u'dis_unicast' not in self.settings.rpl_extensions
            return u'dis_broadcast'
        else:
            return u'disabled'

    @property
    def dis_timer_is_running(self):
        return self.engine.is_scheduled(str(self.mote.id) + u'dis')

    def start_dis_timer(self):
        self.engine.scheduleIn(
            delay          = self.DEFAULT_DIS_INTERVAL_SECONDS,
            cb             = self.handle_dis_timer,
            uniqueTag      = str(self.mote.id) + u'dis',
            intraSlotOrder = d.INTRASLOTORDER_STACKTASKS
        )

    def stop_dis_timer(self):
        self.engine.removeFutureEvent(str(self.mote.id) + u'dis')

    def handle_dis_timer(self):
        self.send_DIS(d.IPV6_ALL_RPL_NODES_ADDRESS)
        self.start_dis_timer()

    def send_DIS(self, dstIp):
        assert dstIp is not None
        dis = {
            u'type': d.PKT_TYPE_DIS,
            u'net' : {
                u'srcIp':         str(self.mote.get_ipv6_link_local_addr()),
                u'dstIp':         dstIp,
                u'packet_length': d.PKT_LEN_DIS
            },
            u'app' : {}
        }
        self.log(
            SimEngine.SimLog.LOG_RPL_DIS_TX,
            {
                u'_mote_id':  self.mote.id,
                u'packet':    dis,
            }
        )
        self.mote.sixlowpan.sendPacket(dis)

    # === DIO

    def _send_DIO(self, dstIp=None):
        if self.dodagId is None:
            # seems we performed local repair
            return

        dio = self._create_DIO(dstIp)

        # log
        self.log(
            SimEngine.SimLog.LOG_RPL_DIO_TX,
            {
                u'_mote_id':  self.mote.id,
                u'packet':    dio,
            }
        )

        self.mote.sixlowpan.sendPacket(dio)

    def _create_DIO(self, dstIp=None):

        assert self.dodagId is not None

        if dstIp is None:
            dstIp = d.IPV6_ALL_RPL_NODES_ADDRESS

        if self.of.rank is None:
            rank = d.RPL_INFINITE_RANK
        else:
            rank = self.of.rank

        # create
        newDIO = {
            u'type':              d.PKT_TYPE_DIO,
            u'app': {
                u'rank':          rank,
                u'dodagId':       self.dodagId,
            },
            u'net': {
                u'srcIp':         self.mote.get_ipv6_link_local_addr(),
                u'dstIp':         dstIp,
                u'packet_length': d.PKT_LEN_DIO
            }
        }

        return newDIO

    def action_receiveDIO(self, packet):

        assert packet[u'type'] == d.PKT_TYPE_DIO

        # abort if I'm not sync'ed (I cannot decrypt the DIO)
        if not self.mote.tsch.getIsSync():
            return

        # abort if I'm not join'ed (I cannot decrypt the DIO)
        if not self.mote.secjoin.getIsJoined():
            return

        # abort if I'm the DAGroot (I don't need to parse a DIO)
        if self.mote.dagRoot:
            return

        # log
        self.log(
            SimEngine.SimLog.LOG_RPL_DIO_RX,
            {
                u'_mote_id':  self.mote.id,
                u'packet':    packet,
            }
        )

        # handle the infinite rank
        if packet[u'app'][u'rank'] == d.RPL_INFINITE_RANK:
            if self.dodagId is None:
                # ignore this DIO
                return
            else:
                # if the DIO has the infinite rank, reset the Trickle timer
                self.trickle_timer.reset()

        # feed our OF with the received DIO
        self.of.update(packet)

        if self.getPreferredParent() is not None:
            # (re)join the RPL network
            self.join_dodag(packet[u'app'][u'dodagId'])

    def join_dodag(self, dodagId=None):
        if dodagId is None:
            # re-join the DODAG without receiving a DIO
            assert self.dodagId is not None
        else:
            self.dodagId = dodagId
        self.mote.add_ipv6_prefix(d.IPV6_DEFAULT_PREFIX)
        self.trickle_timer.start()
        self.trickle_timer.reset()
        self.stop_dis_timer()

    # === DAO

    def _schedule_sendDAO(self, firstDAO=False):
        """
        Schedule to send a DAO sometimes in the future.
        """

        assert self.mote.dagRoot is False

        # abort if DAO disabled
        if self.settings.rpl_daoPeriod == 0:
           # secjoin never completes if downward traffic is not supported by
            # DAO
            assert self.settings.secjoin_enabled is False

            # start sending EBs and application packets.
            self.mote.tsch.startSendingEBs()
            self.mote.app.startSendingData()
            return

        asnNow = self.engine.getAsn()

        if firstDAO:
            asnDiff = 1
        else:
            asnDiff = int(math.ceil(
                old_div(random.uniform(
                    0.8 * self.settings.rpl_daoPeriod,
                    1.2 * self.settings.rpl_daoPeriod
                ), self.settings.tsch_slotDuration))
            )

        # schedule sending a DAO
        self.engine.scheduleAtAsn(
            asn              = asnNow + asnDiff,
            cb               = self._action_sendDAO,
            uniqueTag        = (self.mote.id, u'_action_sendDAO'),
            intraSlotOrder   = d.INTRASLOTORDER_STACKTASKS,
        )

    def _stop_sendDAO(self):
        self.engine.removeFutureEvent((self.mote.id, u'_action_sendDAO'))

    def _action_sendDAO(self):
        """
        Enqueue a DAO and schedule next one.
        """

        if self.of.get_preferred_parent() is None:
            # stop sending DAO
            return

        # enqueue
        self._action_enqueueDAO()

        # the root now knows a source route to me
        # I can serve as join proxy: start sending DIOs and EBs
        # I can send data back-and-forth with an app
        self.mote.tsch.startSendingEBs()    # mote
        self.mote.app.startSendingData()    # mote

        # schedule next DAO
        self._schedule_sendDAO()

    def _action_enqueueDAO(self):
        """
        enqueue a DAO into TSCH queue
        """

        assert not self.mote.dagRoot

        if self.dodagId is None:
            # seems we've lost all the candidate parents; do nothing
            return

        # abort if not ready yet
        if self.mote.clear_to_send_EBs_DATA()==False:
            return

        parent_mac_addr = netaddr.EUI(self.of.get_preferred_parent())
        prefix = netaddr.IPAddress(d.IPV6_DEFAULT_PREFIX)
        parent_ipv6_addr = str(parent_mac_addr.ipv6(prefix))

        # create
        newDAO = {
            u'type':                d.PKT_TYPE_DAO,
            u'app': {
                u'parent_addr':     parent_ipv6_addr,
            },
            u'net': {
                u'srcIp':           self.mote.get_ipv6_global_addr(),
                u'dstIp':           self.dodagId,       # to DAGroot
                u'packet_length':   d.PKT_LEN_DAO,
            },
        }

        # log
        self.log(
            SimEngine.SimLog.LOG_RPL_DAO_TX,
            {
                u'_mote_id': self.mote.id,
                u'packet':   newDAO,
            }
        )

        # remove other possible DAOs from the queue
        self.mote.tsch.remove_packets_in_tx_queue(type=d.PKT_TYPE_DAO)

        # send
        self.mote.sixlowpan.sendPacket(newDAO)

    def action_receiveDAO(self, packet):
        """
        DAGroot receives DAO, store parent/child relationship for source route calculation.
        """

        assert self.mote.dagRoot

        # log
        self.log(
            SimEngine.SimLog.LOG_RPL_DAO_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet':   packet,
            }
        )

        # store parent/child relationship for source route calculation
        self.addParentChildfromDAOs(
            parent_addr   = packet[u'app'][u'parent_addr'],
            child_addr    = packet[u'net'][u'srcIp']
        )

    # source route

    def computeSourceRoute(self, dst_addr):
        assert self.mote.dagRoot
        try:
            sourceRoute = []
            cur_addr = dst_addr
            while self.mote.is_my_ipv6_addr(cur_addr) is False:
                sourceRoute += [cur_addr]
                cur_addr     = self.parentChildfromDAOs[cur_addr]
                if cur_addr in sourceRoute:
                    # routing loop is detected; cannot return an effective
                    # source-routing header
                    returnVal = None
                    break
        except KeyError:
            returnVal = None
        else:
            # reverse (so goes from source to destination)
            sourceRoute.reverse()

            returnVal = sourceRoute

        return returnVal


class RplOFBase(object):
    def __init__(self, rpl):
        self.rpl = rpl
        self.rank = None
        self.preferred_parent = None

    def reset(self):
        self.rank = None
        old_parent_mac_addr = self.get_preferred_parent()
        self.preferred_parent = None
        self.rpl.indicate_preferred_parent_change(
            old_preferred = old_parent_mac_addr,
            new_preferred = None
        )

    def update(self, dio):
        pass

    def update_etx(self, cell, mac_addr, isACKed):
        pass

    def get_preferred_parent(self):
        return self.preferred_parent

    def poison_rpl_parent(self, mac_addr):
        pass


class RplOFNone(RplOFBase):
    def set_rank(self, new_rank):
        self.rank = new_rank

    def set_preferred_parent(self, new_preferred_parent):
        self.preferred_parent = new_preferred_parent


class RplOF0(RplOFBase):

    # Constants defined in RFC 6550
    INFINITE_RANK = 65535

    # Constants defined in RFC 8180
    UPPER_LIMIT_OF_ACCEPTABLE_ETX = 3
    MINIMUM_STEP_OF_RANK = 1
    MAXIMUM_STEP_OF_RANK = 9

    # Custom constants
    MAX_NUM_OF_CONSECUTIVE_FAILURES_WITHOUT_SUCCESS = 10
    ETX_DEFAULT = UPPER_LIMIT_OF_ACCEPTABLE_ETX
    # if we have a "good" link to the parent, stay with the parent even if the
    # rank of the parent is worse than the best neighbor by more than
    # PARENT_SWITCH_RANK_THRESHOLD. rank_increase is computed as per Section
    # 5.1.1. of RFC 8180.
    ETX_GOOD_LINK = 2
    PARENT_SWITCH_RANK_INCREASE_THRESHOLD = (
        ((3 * ETX_GOOD_LINK) - 2) * d.RPL_MINHOPRANKINCREASE
    )
    # The number of transmissions that is needed for ETX calculation
    ETX_NUM_TX_CUTOFF = 100

    def __init__(self, rpl):
        super(RplOF0, self).__init__(rpl)
        self.neighbors = []

    @property
    def parents(self):
        # a parent should have a lower rank than us by MinHopRankIncrease at
        # least. See section 3.5.1 of RFC 6550:
        #    "MinHopRankIncrease is the minimum increase in Rank between a node
        #     and any of its DODAG parents."
        _parents = []
        for neighbor in self.neighbors:
            if self._calculate_rank(neighbor) is None:
                # skip this one
                continue

            if (
                    (self.rank is None)
                    or
                    (
                        d.RPL_MINHOPRANKINCREASE <=
                        self.rank - neighbor[u'advertised_rank']
                    )
                ):
                _parents.append(neighbor)

        return _parents

    def reset(self):
        self.neighbors = []
        super(RplOF0, self).reset()

    def update(self, dio):
        mac_addr = dio[u'mac'][u'srcMac']
        rank = dio[u'app'][u'rank']

        # update neighbor's rank
        neighbor = self._find_neighbor(mac_addr)
        if neighbor is None:
            neighbor = self._add_neighbor(mac_addr)
        self._update_neighbor_rank(neighbor, rank)

        # if we received the infinite rank from our preferred parent,
        # invalidate our rank
        if (
                (self.preferred_parent == neighbor)
                and
                (rank == d.RPL_INFINITE_RANK)
            ):
            self.rank = None

        # change preferred parent if necessary
        self._update_preferred_parent()

    def get_preferred_parent(self):
        if self.preferred_parent is None:
            return None
        else:
            return self.preferred_parent[u'mac_addr']

    def poison_rpl_parent(self, mac_addr):
        if mac_addr is None:
            neighbor = None
        else:
            neighbor = self._find_neighbor(mac_addr)

        if neighbor:
            self._update_neighbor_rank(neighbor, d.RPL_INFINITE_RANK)
            self.rank = None
            self._update_preferred_parent()

    def update_etx(self, cell, mac_addr, isACKed):
        assert mac_addr != d.BROADCAST_ADDRESS
        assert d.CELLOPTION_TX in cell.options

        neighbor = self._find_neighbor(mac_addr)
        if neighbor is None:
            # we've not received DIOs from this neighbor; ignore the neighbor
            return

        if cell.mac_addr is None:
            # we calculate ETX only on dedicated cells
            # XXX: Although it'd be better to exclude cells having
            # SHARED bit on as well, this is not good for the
            # autonomous cell defined by MSF.
            return

        neighbor[u'numTx'] += 1
        if isACKed is True:
            neighbor[u'numTxAck'] += 1

        if neighbor[u'numTx'] >= self.ETX_NUM_TX_CUTOFF:
            # update ETX
            assert neighbor[u'numTxAck'] > 0
            neighbor[u'etx'] = float(neighbor[u'numTx']) / neighbor[u'numTxAck']
            # reset counters
            neighbor[u'numTx'] = 0
            neighbor[u'numTxAck'] = 0
        elif (
                (neighbor[u'numTxAck'] == 0)
                and
                (
                    self.MAX_NUM_OF_CONSECUTIVE_FAILURES_WITHOUT_SUCCESS <=
                    neighbor[u'numTx']
                )
            ):
            # set invalid ETX
            neighbor[u'etx'] = self.UPPER_LIMIT_OF_ACCEPTABLE_ETX + 1

        self._update_neighbor_rank_increase(neighbor)
        self._update_preferred_parent()

    def _add_neighbor(self, mac_addr):
        assert self._find_neighbor(mac_addr) is None

        neighbor = {
            u'mac_addr': mac_addr,
            u'advertised_rank': None,
            u'rank_increase': None,
            u'numTx': 0,
            u'numTxAck': 0,
            u'etx': self.ETX_DEFAULT
        }
        self.neighbors.append(neighbor)
        self._update_neighbor_rank_increase(neighbor)
        return neighbor

    def _find_neighbor(self, mac_addr):
        for neighbor in self.neighbors:
            if neighbor[u'mac_addr'] == mac_addr:
                return neighbor
        return None

    def _update_neighbor_rank(self, neighbor, new_advertised_rank):
        neighbor[u'advertised_rank'] = new_advertised_rank

    def _update_neighbor_rank_increase(self, neighbor):
        if neighbor[u'etx'] > self.UPPER_LIMIT_OF_ACCEPTABLE_ETX:
            step_of_rank = None
        else:
            # step_of_rank is strictly positive integer as per RFC6552
            step_of_rank = int((3 * neighbor[u'etx']) - 2)

        if step_of_rank is None:
            # this neighbor will not be considered as a parent
            neighbor[u'rank_increase'] = None
        else:
            assert self.MINIMUM_STEP_OF_RANK <= step_of_rank
            # step_of_rank never exceeds 7 because the upper limit of acceptable
            # ETX is 3, which is defined in Section 5.1.1 of RFC 8180
            assert step_of_rank <= self.MAXIMUM_STEP_OF_RANK
            neighbor[u'rank_increase'] = step_of_rank * d.RPL_MINHOPRANKINCREASE

        if neighbor == self.preferred_parent:
            self.rank = self._calculate_rank(self.preferred_parent)

    def _calculate_rank(self, neighbor):
        if (
                (neighbor is None)
                or
                (neighbor[u'advertised_rank'] is None)
                or
                (neighbor[u'rank_increase'] is None)
            ):
            return None
        elif neighbor[u'advertised_rank'] == self.INFINITE_RANK:
            # this neighbor should be ignored
            return None
        else:
            rank = neighbor[u'advertised_rank'] + neighbor[u'rank_increase']

            if rank > self.INFINITE_RANK:
                return self.INFINITE_RANK
            else:
                return rank

    def _update_preferred_parent(self):
        if (
                (self.preferred_parent is not None)
                and
                (self.preferred_parent[u'advertised_rank'] is not None)
                and
                (self.rank is not None)
                and
                (
                    (self.preferred_parent[u'advertised_rank'] - self.rank) <
                    d.RPL_PARENT_SWITCH_RANK_THRESHOLD
                )
                and
                (
                    self.preferred_parent[u'rank_increase'] <
                    self.PARENT_SWITCH_RANK_INCREASE_THRESHOLD
                )
            ):
            # stay with the current parent. the link to the parent is
            # good. but, if the parent rank is higher than us and the
            # difference is more than d.RPL_PARENT_SWITCH_RANK_THRESHOLD, we dump
            # the parent. otherwise, we may create a routing loop.
            return

        try:
            candidate = min(self.parents, key=self._calculate_rank)
            new_rank = self._calculate_rank(candidate)
        except ValueError:
            # self.parents is empty
            candidate = None
            new_rank = None

        if new_rank is None:
            # we don't have any available parent
            new_parent = None
        elif self.rank is None:
            new_parent = candidate
            self.rank = new_rank
        else:
            # (new_rank is not None) and (self.rank is None)
            rank_difference = self.rank - new_rank

            # Section 6.4, RFC 8180
            #
            #   Per [RFC6552] and [RFC6719], the specification RECOMMENDS the
            #   use of a boundary value (PARENT_SWITCH_RANK_THRESHOLD) to avoid
            #   constant changes of the parent when ranks are compared.  When
            #   evaluating a parent that belongs to a smaller path cost than
            #   the current minimum path, the candidate node is selected as the
            #   new parent only if the difference between the new path and the
            #   current path is greater than the defined
            #   PARENT_SWITCH_RANK_THRESHOLD.

            if rank_difference is not None:
                if d.RPL_PARENT_SWITCH_RANK_THRESHOLD < rank_difference:
                    new_parent = candidate
                    self.rank = new_rank
                else:
                    # no change on preferred parent
                    new_parent = self.preferred_parent

        if (
                (new_parent is not None)
                and
                (new_parent != self.preferred_parent)
            ):
            # change to the new preferred parent

            if self.preferred_parent is None:
                old_parent_mac_addr = None
            else:
                old_parent_mac_addr = self.preferred_parent[u'mac_addr']

            self.preferred_parent = new_parent
            if new_parent is None:
                new_parent_mac_addr = None
            else:
                new_parent_mac_addr = self.preferred_parent[u'mac_addr']

            self.rpl.indicate_preferred_parent_change(
                old_preferred = old_parent_mac_addr,
                new_preferred = new_parent_mac_addr
            )

            # reset Trickle Timer
            self.rpl.trickle_timer.reset()
        elif (
                (new_parent is None)
                and
                (self.preferred_parent is not None)
            ):
            self.rpl.local_repair()
        else:
            # do nothing
            pass


class RplOFBestLinkPDR(RplOF0):
    ACCEPTABLE_LOWEST_PDR  = 1.0 / RplOF0.UPPER_LIMIT_OF_ACCEPTABLE_ETX
    INVALID_RSSI_VALUE = -1000
    NONE_PREFERRED_PARENT = {
        u'mac_addr': None,
        u'mote_id': None,
        u'rank': d.RPL_INFINITE_RANK,
        u'mean_link_pdr': 0,
        u'mean_link_rssi': INVALID_RSSI_VALUE
    }

    def __init__(self, rpl):
        super(RplOFBestLinkPDR, self).__init__(rpl)
        self.preferred_parent = self.NONE_PREFERRED_PARENT
        self.neighbors = []
        self.path_pdr = 0

        # short hand
        self.mote = self.rpl.mote
        self.engine = self.rpl.engine
        self.connectivity = self.engine.connectivity

    @property
    def parents(self):
        # return neighbors which don't have us on their paths to the
        # root
        ret_val = []
        for neighbor in self.neighbors:
            # parent should have better PDR than ACCEPTABLE_LOWEST_PDR
            if neighbor[u'mean_link_pdr'] < self.ACCEPTABLE_LOWEST_PDR:
                # this neighbor is not eligible to be a parent
                continue
            parent_mote = self.engine.motes[neighbor[u'mote_id']]
            while parent_mote.dagRoot is False:
                assert parent_mote.rpl.of.preferred_parent
                parent_id = parent_mote.rpl.of.preferred_parent[u'mote_id']

                if (
                        (parent_id is None)
                        or
                        (parent_id == self.mote.id)
                    ):
                    # this mote doesn't have parent. OR we will make a
                    # routing loop if we select this neighbor as our
                    # preferred parent.
                    parent_mote = None
                    break

                parent_mote = self.engine.motes[parent_id]

            if parent_mote:
                ret_val.append(neighbor)
        return ret_val

    def reset(self):
        super(RplOFBestLinkPDR, self).reset()
        self.preferred_parent = self.NONE_PREFERRED_PARENT
        self.neighbors = []

    def update(self, dio):
        # short-hand
        src_mac = dio[u'mac'][u'srcMac']

        # update the 'parent' associated with the source MAC address
        neighbor = self._find_neighbor(src_mac)
        if dio[u'app'][u'rank'] == d.RPL_INFINITE_RANK:
            if neighbor is None:
                # do nothing
                pass
            else:
                # remove the neighbor advertising the infinite rank
                self.neighbors.remove(neighbor)
        else:
            if neighbor is None:
                # add a new neighbor entry
                neighbor = {
                    u'mac_addr': src_mac,
                    u'mote_id': self._find_mote_id(src_mac),
                    u'rank': None,
                    u'mean_link_pdr': 0
                }
                self.neighbors.append(neighbor)

            # update the advertised rank and path ETX
            neighbor[u'rank'] = dio[u'app'][u'rank']

        # update the PDR values
        self._update_link_quality_of_neighbors()

        # select the best neighbor the link to whom is the heighest PDR
        self._update_preferred_parent()

    def poison_rpl_parent(self, mac_addr):
        neighbor = self._find_neighbor(mac_addr)
        if neighbor is not None:
            neighbor[u'rank'] = d.RPL_INFINITE_RANK
        self._update_preferred_parent()
        # send a broadcast DIS to collect neighbors which we've not
        # noticed
        self.rpl.send_DIS(d.IPV6_ALL_RPL_NODES_ADDRESS)

    def update_etx(self, cell, mac_addr, isACKed):
        # check the current PDR and RSSI values of the links to our
        # parents
        self._update_link_quality_of_neighbors()

        # update the preferred parent if necessary
        previous_parent = self.preferred_parent
        self._update_preferred_parent()

        if (
                (previous_parent == self.NONE_PREFERRED_PARENT)
                and
                (previous_parent != self.preferred_parent)
            ):
            # rejoin the DODAG
            self.rpl.join_dodag()

    @staticmethod
    def _calculate_rank(neighbor):
        # calculate ETX by inverting the path PDR and apply it to the
        # fomula defined by RFC8180 for OF0
        if (
                (neighbor[u'rank'] == d.RPL_INFINITE_RANK)
                or
                (neighbor[u'mean_link_pdr'] == 0)
            ):
            rank = d.RPL_INFINITE_RANK
        else:
            etx = old_div(1, neighbor[u'mean_link_pdr'])
            step_of_rank = int(3 * etx - 2)
            rank_increase = step_of_rank * d.RPL_MINHOPRANKINCREASE
            rank = neighbor[u'rank'] + rank_increase
        return rank

    def _find_neighbor(self, mac_addr):
        ret_val = None
        for neighbor in self.neighbors:
            if neighbor[u'mac_addr'] == mac_addr:
                ret_val = neighbor
                break
        return ret_val

    def _find_mote_id(self, mac_addr):
        mote_id = None
        for mote in self.engine.motes:
            if mote.is_my_mac_addr(mac_addr):
                mote_id = mote.id
                break
        assert mote_id is not None
        return mote_id

    def _update_link_quality_of_neighbors(self):
        for neighbor in self.neighbors:
            self._update_mean_link_pdr(neighbor)
            self._update_mean_link_rssi(neighbor)

    def _update_preferred_parent(self):
        if self.parents:
            new_preferred_parent = self._find_best_parent()
            new_rank = self._calculate_rank(new_preferred_parent)
        else:
            new_preferred_parent = self.NONE_PREFERRED_PARENT
            new_rank = d.RPL_INFINITE_RANK

        if (
                (new_preferred_parent != self.NONE_PREFERRED_PARENT)
                and
                (new_rank == d.RPL_INFINITE_RANK)
                and
                (self.preferred_parent != self.NONE_PREFERRED_PARENT)
            ):
            # we have only a parent having a bad rank or bad PDR; set
            # None to new_preferred_parent in order to trigger parent
            # switch
            new_preferred_parent = self.NONE_PREFERRED_PARENT

        if new_preferred_parent != self.preferred_parent:
            if (
                    (new_preferred_parent == self.NONE_PREFERRED_PARENT)
                    or
                    (
                        d.RPL_PARENT_SWITCH_RANK_THRESHOLD <
                        (self._calculate_rank(self.preferred_parent) - new_rank)
                    )
                ):
                # we're going to swith to the new parent, which may be
                # NONE_PREFERRED_PARENT
                old_preferred_parent = self.preferred_parent
                self.preferred_parent = new_preferred_parent
                self.rank = self._calculate_rank(new_preferred_parent)
                self.rpl.indicate_preferred_parent_change(
                    old_preferred_parent[u'mac_addr'],
                    new_preferred_parent[u'mac_addr']
                )

                if (
                        (
                            self._calculate_rank(old_preferred_parent) ==
                            d.RPL_INFINITE_RANK
                        )
                        and
                        (old_preferred_parent in self.neighbors)
                    ):
                    # this neighbor should have been poisoned; remove
                    # this one from our neighbor list
                    self.neighbors.remove(old_preferred_parent)

    def _update_mean_link_pdr(self, neighbor):
        # we will calculate the mean PDR value over all the available
        # channels and both of the directions
        neighbor[u'mean_link_pdr'] = numpy.mean([
            self.connectivity.get_pdr(src_id, dst_id, channel)
            for channel in self.mote.tsch.hopping_sequence
            for src_id, dst_id in [
                (self.mote.id, neighbor[u'mote_id']),
                (neighbor[u'mote_id'], self.mote.id)
            ]
        ])

    def _update_mean_link_rssi(self, neighbor):
        # we will calculate the mean RSSI value over all the available
        # channels.
        neighbor[u'mean_link_rssi'] = numpy.mean([
            self.connectivity.get_rssi(
                src_id = self.mote.id,
                dst_id = neighbor[u'mote_id'],
                channel = channel
            )
            for channel in self.mote.tsch.hopping_sequence
        ])

    def _find_best_parent(self):
        # find a parent which brings the best rank for us. use mote_id
        # for a tie-breaker.

        # sort the neighbors
        self.neighbors = sorted(
            self.neighbors,
            key=lambda e: (
                self._calculate_rank(e),
                e[u'mean_link_rssi'],
                e[u'mote_id']
            )
        )

        # then return the first neighbor in "parents"
        return self.parents[0]
