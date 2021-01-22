"""
Secure joining layer of a mote.
"""
from __future__ import absolute_import
from __future__ import division

# =========================== imports =========================================

from builtins import str
from builtins import object
from past.utils import old_div
import copy
import random

# Mote sub-modules
from . import MoteDefines as d

# Simulator-wide modules
import SimEngine
from SimEngine.Mote.sf import SchedulingFunctionMSF

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

class SecJoin(object):

    # parameters from draft-ietf-6tisch-minimal-security
    TIMEOUT_BASE          = 10
    TIMEOUT_RANDOM_FACTOR = 1.5
    MAX_RETRANSMIT        = 4

    def __init__(self, mote):

        # store params
        self.mote                           = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine                         = SimEngine.SimEngine.SimEngine()
        self.settings                       = SimEngine.SimSettings.SimSettings()
        self.log                            = SimEngine.SimLog.SimLog().log

        # local variables
        self._isJoined                      = False
        self._request_timeout               = None
        self._retransmission_count          = None
        self._retransmission_tag            = (self.mote.id, u'_retransmit_join_request')

    #======================== public ==========================================

    # getters/setters

    def setIsJoined(self, value):
        if value:
            self.log(
                SimEngine.SimLog.LOG_SECJOIN_JOINED,
                {
                    u'_mote_id': self.mote.id,
                }
            )
            self.mote.rpl.start()
        elif self._isJoined:
            self.log(
                SimEngine.SimLog.LOG_SECJOIN_UNJOINED,
                {
                    u'_mote_id': self.mote.id,
                }
            )
            self.mote.rpl.stop()
        else:
            self.log(
                SimEngine.SimLog.LOG_SECJOIN_FAILED,
                {
                    u'_mote_id': self.mote.id,
                }
            )
        self._isJoined = value

    def getIsJoined(self):
        return self._isJoined

    # admin

    def startJoinProcess(self):

        assert self.mote.dagRoot==False

        if not self.mote.tsch.getIsSync():
            return

        if self.getIsJoined():
            # we've already joined
            return

        assert self.mote.tsch.join_proxy!=None

        if self.settings.secjoin_enabled:
            self._retransmission_count = 0

            # initialize request timeout; pick a number randomly between
            # TIMEOUT_BASE and (TIMEOUT_BASE * TIMEOUT_RANDOM_FACTOR)
            self._request_timeout  = self.TIMEOUT_BASE * random.uniform(1, self.TIMEOUT_RANDOM_FACTOR)

            self._send_join_request()
        else:
            # consider I'm already joined
            self.setIsJoined(True)  # forced (secjoin_enabled==False)

    # from lower stack

    def receive(self, packet):

        if   packet[u'type'] == d.PKT_TYPE_JOIN_REQUEST:

            if self.mote.dagRoot is False:
                # I'm the join proxy

                if self.mote.rpl.dodagId is None:
                    # ignore this request; we may have performed the local
                    # repair
                    return

                # proxy join request to dagRoot
                proxiedJoinRequest = {
                    u'type':                 d.PKT_TYPE_JOIN_REQUEST,
                    u'app': {
                        u'stateless_proxy': {
                            u'pledge_addr':  packet[u'net'][u'srcIp']
                        }
                    },
                    u'net': {
                        u'srcIp':            self.mote.get_ipv6_global_addr(),
                        u'dstIp':            self.mote.rpl.dodagId,
                        u'packet_length':    packet[u'net'][u'packet_length'],
                    },
                }

                # send proxied join response
                self.mote.sixlowpan.sendPacket(proxiedJoinRequest)

            else:
                # I'm the dagRoot

                # echo back 'stateless_proxy' element in the join response, if present in the join request
                app = {}
                if u'stateless_proxy' in packet[u'app']:
                    app[u'stateless_proxy'] = copy.deepcopy(packet[u'app'][u'stateless_proxy'])
                    src_ip = self.mote.get_ipv6_global_addr()
                else:
                    src_ip = self.mote.get_ipv6_link_local_addr()

                # format join response
                joinResponse = {
                    u'type':                 d.PKT_TYPE_JOIN_RESPONSE,
                    u'app':                  app,
                    u'net': {
                        u'srcIp':            src_ip,
                        u'dstIp':            packet[u'net'][u'srcIp'],            # to join proxy
                        u'packet_length':    d.PKT_LEN_JOIN_RESPONSE,
                    },
                }

                # send join response
                self.mote.sixlowpan.sendPacket(joinResponse)

        elif packet[u'type']== d.PKT_TYPE_JOIN_RESPONSE:
            assert self.mote.dagRoot==False

            if self.getIsJoined()==True:
                # I'm the join proxy

                if u'stateless_proxy' not in packet[u'app']:
                    # this must be a duplicate response; ignore it
                    pass
                else:
                    # remove the 'stateless_proxy' element from the app payload
                    app         = copy.deepcopy(packet[u'app'])
                    pledge_addr = app[u'stateless_proxy'][u'pledge_addr']
                    del app[u'stateless_proxy']

                    # proxy join response to pledge
                    proxiedJoinResponse = {
                        u'type':                 d.PKT_TYPE_JOIN_RESPONSE,
                        u'app':                  app,
                        u'net': {
                            u'srcIp':            self.mote.get_ipv6_link_local_addr(),
                            u'dstIp':            pledge_addr,
                            u'packet_length':    packet[u'net'][u'packet_length'],
                        },
                    }

                    # send proxied join response
                    self.mote.sixlowpan.sendPacket(proxiedJoinResponse)

            else:
                # I'm the pledge

                if self._retransmission_count is None:
                    # now it's not in the middle of a secjoin process:
                    # this response corresponds to a request which this mote
                    # had sent before it left the network; ignore this response
                    return

                # cancel the event for retransmission
                self.engine.removeFutureEvent(self._retransmission_tag)

                # I'm now joined!
                self.setIsJoined(True)  # mote
        else:
            raise SystemError()

    #======================== private ==========================================

    def _retransmit_join_request(self):
        if not self.mote.tsch.getIsSync():
            # we are desynchronized; give it up
            return
        elif  self.getIsJoined() is True:
            # do nothing; this could happen when it received a response at the
            # same slot
            pass
        elif self._retransmission_count == self.MAX_RETRANSMIT:

            self.log(
                SimEngine.SimLog.LOG_SECJOIN_FAILED,
                {
                    u'_mote_id': self.mote.id,
                }
            )

            # Back to listening phase, although
            # draft-ietf-6tisch-minimal-security says, "If the retransmission
            # counter reaches MAX_RETRANSMIT on a timeout, the pledge SHOULD
            # attempt to join the next advertised 6TiSCH network."
            self._request_timeout      = None
            self._retransmission_count = None
            self.mote.tsch.setIsSync(False)
        elif self._retransmission_count < self.MAX_RETRANSMIT:
            # double the timeout value
            self._request_timeout *= 2
            self._retransmission_count += 1
            # retransmit the request
            self._send_join_request()
        else:
            # shouldn't happen
            assert False

    def _send_join_request(self):
        # log
        self.log(
            SimEngine.SimLog.LOG_SECJOIN_TX,
            {
                u'_mote_id': self.mote.id,
            }
        )

        # create join request
        joinRequest = {
            u'type':                     d.PKT_TYPE_JOIN_REQUEST,
            u'app': {
            },
            u'net': {
                u'srcIp':                self.mote.get_ipv6_link_local_addr(),
                u'dstIp':                str(self.mote.tsch.join_proxy.ipv6_link_local()),
                u'packet_length':        d.PKT_LEN_JOIN_REQUEST,
            },
        }

        # send join request
        self.mote.sixlowpan.sendPacket(joinRequest)

        # convert seconds to slots
        target_asn = (
            self.engine.getAsn() +
            int(old_div(self._request_timeout, self.settings.tsch_slotDuration))
        )
        self.engine.scheduleAtAsn(
            asn              = target_asn,
            cb               = self._retransmit_join_request,
            uniqueTag        = self._retransmission_tag,
            intraSlotOrder   = d.INTRASLOTORDER_STACKTASKS
        )
