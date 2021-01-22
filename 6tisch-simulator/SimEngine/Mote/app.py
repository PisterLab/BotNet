"""
An application lives on each node
"""
from __future__ import absolute_import

# =========================== imports =========================================

from builtins import range
from builtins import object
from abc import abstractmethod
import random

# Mote sub-modules

# Simulator-wide modules
import SimEngine
from . import MoteDefines as d

# =========================== defines =========================================

# =========================== helpers =========================================

# =========================== body ============================================

def App(mote):
    """factory method for application
    """

    settings = SimEngine.SimSettings.SimSettings()

    # use mote.id to determine whether it is the root or not instead of using
    # mote.dagRoot because mote.dagRoot is not initialized when application is
    # instantiated
    if mote.id == 0:
        return AppRoot(mote)
    else:
        return globals()[settings.app](mote)

class AppBase(object):
    """Base class for Applications.
    """

    def __init__(self, mote, **kwargs):

        # store params
        self.mote       = mote

        # singletons (quicker access, instead of recreating every time)
        self.engine     = SimEngine.SimEngine.SimEngine()
        self.settings   = SimEngine.SimSettings.SimSettings()
        self.log        = SimEngine.SimLog.SimLog().log

        # local variables
        self.appcounter = 0

    #======================== public ==========================================

    @abstractmethod
    def startSendingData(self):
        """Starts the application process.

        Typically, this methods schedules an event to send a packet to the root.
        """
        raise NotImplementedError()  # abstractmethod

    def recvPacket(self, packet):
        """Receive a packet destined to this application
        """
        # log and mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet'  : packet
            }
        )

    #======================== private ==========================================

    def _generate_packet(
            self,
            dstIp,
            packet_type,
            packet_length,
        ):

        # create data packet
        dataPacket = {
            u'type':              packet_type,
            u'net': {
                u'srcIp':         self.mote.get_ipv6_global_addr(),
                u'dstIp':         dstIp,
                u'packet_length': packet_length
            },
            u'app': {
                u'appcounter':    self.appcounter,
                u'timestamp':     self.engine.getAsn()
            }

        }

        # update appcounter
        self.appcounter += 1

        return dataPacket

    def _send_packet(self, dstIp, packet_length):

        # abort if I'm not ready to send DATA yet
        if self.mote.clear_to_send_EBs_DATA()==False:
            return

        # create
        packet = self._generate_packet(
            dstIp          = dstIp,
            packet_type    = d.PKT_TYPE_DATA,
            packet_length  = packet_length
        )

        # log
        self.log(
            SimEngine.SimLog.LOG_APP_TX,
            {
                u'_mote_id':       self.mote.id,
                u'packet':         packet,
            }
        )

        # send
        self.mote.sixlowpan.sendPacket(packet)

class AppRoot(AppBase):
    """Handle application packets from motes
    """

    # the payload length of application ACK
    APP_PK_LENGTH = 10

    def __init__(self, mote):
        super(AppRoot, self).__init__(mote)

    #======================== public ==========================================

    def startSendingData(self):
        # nothing to schedule
        pass

    def recvPacket(self, packet):
        assert self.mote.dagRoot

        # log and update mote stats
        self.log(
            SimEngine.SimLog.LOG_APP_RX,
            {
                u'_mote_id': self.mote.id,
                u'packet'  : packet
            }
        )

    #======================== private ==========================================

    def _send_ack(self, destination, packet_length=None):

        if packet_length is None:
            packet_length = self.APP_PK_LENGTH

        self._send_packet(
            dstIp          = destination,
            packet_length  = packet_length
        )

class AppPeriodic(AppBase):

    """Send a packet periodically

    Intervals are distributed uniformly between (pkPeriod-pkPeriodVar)
    and (pkPeriod+pkPeriodVar).

    The first timing to send a packet is randomly chosen between [next
    asn, (next asn + pkPeriod)].
    """

    def __init__(self, mote, **kwargs):
        super(AppPeriodic, self).__init__(mote)
        self.sending_first_packet = True

    #======================== public ==========================================

    def startSendingData(self):
        if self.sending_first_packet:
            self._schedule_transmission()

    #======================== public ==========================================

    def _schedule_transmission(self):
        assert self.settings.app_pkPeriod >= 0
        if self.settings.app_pkPeriod == 0:
            return

        if self.sending_first_packet:
            # compute initial time within the range of [next asn, next asn+pkPeriod]
            delay = self.settings.tsch_slotDuration + (self.settings.app_pkPeriod * random.random())
            self.sending_first_packet = False
        else:
            # compute random delay
            assert self.settings.app_pkPeriodVar < 1
            delay = self.settings.app_pkPeriod * (1 + random.uniform(-self.settings.app_pkPeriodVar, self.settings.app_pkPeriodVar))

        # schedule
        self.engine.scheduleIn(
            delay           = delay,
            cb              = self._send_a_single_packet,
            uniqueTag       = (
                u'AppPeriodic',
                u'scheduled_by_{0}'.format(self.mote.id)
            ),
            intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
        )

    def _send_a_single_packet(self):
        if self.mote.rpl.dodagId == None:
            # it seems we left the dodag; stop the transmission
            self.sending_first_packet = True
            return

        self._send_packet(
            dstIp          = self.mote.rpl.dodagId,
            packet_length  = self.settings.app_pkLength
        )
        # schedule the next transmission
        self._schedule_transmission()

class AppBurst(AppBase):
    """Generate burst traffic to the root at the specified time (only once)
    """

    #======================== public ==========================================
    def __init__(self, mote, **kwargs):
        super(AppBurst, self).__init__(mote, **kwargs)
        self.done = False

    def startSendingData(self):
        if not self.done:
            # schedule app_burstNumPackets packets in app_burstTimestamp
            self.engine.scheduleIn(
                delay           = self.settings.app_burstTimestamp,
                cb              = self._send_burst_packets,
                uniqueTag       = (
                    u'AppBurst',
                    u'scheduled_by_{0}'.format(self.mote.id)
                ),
                intraSlotOrder  = d.INTRASLOTORDER_ADMINTASKS,
            )
            self.done = True

    #======================== private ==========================================

    def _send_burst_packets(self):
        if self.mote.rpl.dodagId == None:
            # we're not part of the network now
            return

        for _ in range(0, self.settings.app_burstNumPackets):
            self._send_packet(
                dstIp         = self.mote.rpl.dodagId,
                packet_length = self.settings.app_pkLength
            )
