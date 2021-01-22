''"""
Model of a 6TiSCH mote.
"""
from __future__ import absolute_import

# =========================== imports =========================================

from builtins import str
from builtins import object
import threading

import netaddr

# Mote sub-modules
from . import app
from . import secjoin
from . import rpl
from . import sixlowpan
from . import sf
from . import sixp
from . import tsch
from . import radio

from . import MoteDefines as d

# Simulator-wide modules
import SimEngine

# =========================== defines =========================================

# =========================== body ============================================

class Mote(object):

    MAC_ADDR_TYPE_EUI64       = u'eui64'
    IPV6_ADDR_TYPE_LINK_LOCAL = u'link-local'
    IPV6_ADDR_TYPE_GLOBAL     = u'global'

    def __init__(self, id, eui64=None):

        # store params
        self.id                        = id

        # admin
        self.dataLock                  = threading.RLock()

        # singletons (quicker access, instead of recreating every time)
        self.log                       = SimEngine.SimLog.SimLog().log
        self.engine                    = SimEngine.SimEngine.SimEngine()
        self.settings                  = SimEngine.SimSettings.SimSettings()

        # stack state
        self.dagRoot                   = False
        self._init_eui64(eui64)
        self.ipv6_prefix               = None

        # stack
        self.app                       = app.App(self)
        self.secjoin                   = secjoin.SecJoin(self)
        self.rpl                       = rpl.Rpl(self)
        self.sixlowpan                 = sixlowpan.Sixlowpan(self)
        self.sf                        = sf.SchedulingFunction(self)
        self.sixp                      = sixp.SixP(self)
        self.tsch                      = tsch.Tsch(self)
        self.radio                     = radio.Radio(self)

    # ======================= stack ===========================================

    # ===== role

    def setDagRoot(self):
        self.dagRoot         = True
        self.add_ipv6_prefix(d.IPV6_DEFAULT_PREFIX)

    # ==== address

    def is_my_ipv6_addr(self, ipv6_addr):
        # get a address string in the canonical format
        target_ipv6_addr = str(netaddr.IPAddress(ipv6_addr))
        return (
            (self.get_ipv6_global_addr() == target_ipv6_addr)
            or
            (self.get_ipv6_link_local_addr() == target_ipv6_addr)
        )

    def is_my_mac_addr(self, mac_addr):
        return self.eui64 == mac_addr

    def add_ipv6_prefix(self, prefix):
        # having more than one prefix is not supported
        self.ipv6_prefix = netaddr.IPAddress(prefix)
        self.log(
            SimEngine.SimLog.LOG_IPV6_ADD_ADDR,
            {
                u'_mote_id': self.id,
                u'type'    : self.IPV6_ADDR_TYPE_GLOBAL,
                u'addr'    : self.get_ipv6_global_addr()
            }
        )

    def delete_ipv6_prefix(self):
        # having more than one prefix is not supported
        self.ipv6_prefix = None

    def get_ipv6_global_addr(self, ref_addr=None):
        if self.ipv6_prefix is None:
            return None
        else:
            return str(self.eui64.ipv6(self.ipv6_prefix))

    def get_ipv6_link_local_addr(self):
        return str(self.eui64.ipv6_link_local())

    def get_mac_addr(self):
        return str(self.eui64)


    # ==== location

    def setLocation(self, x, y):
        with self.dataLock:
            self.x = x
            self.y = y

    def getLocation(self):
        with self.dataLock:
            return self.x, self.y

    def boot(self):

        if self.dagRoot:
            # I'm the DAG root

            # app
            self.app.startSendingData()     # dagRoot
            # secjoin
            self.secjoin.setIsJoined(True)  # dagRoot
            # rpl
            self.rpl.start()
            # tsch
            self.tsch.clock.sync()
            self.tsch.setIsSync(True)       # dagRoot
            self.tsch.add_minimal_cell()    # dagRpot
            self.tsch.startSendingEBs()     # dagRoot

        else:
            # I'm NOT the DAG root

            # schedule the first listeningForE cell
            self.tsch.schedule_next_listeningForEB_cell()

    # ==== EBs and DIOs

    def clear_to_send_EBs_DATA(self):
        returnVal = True

        # I need to be synchronized
        if returnVal is True:
            if self.tsch.getIsSync() is False:
                returnVal = False

        # I need to have joined
        if returnVal is True:
            if self.secjoin.getIsJoined() is False:
                returnVal = False

        # I must have a preferred parent (or be the dagRoot)
        if returnVal is True:
            if (
                    (self.dagRoot is False)
                    and
                    (self.rpl.getPreferredParent() is None)
                ):
                returnVal = False

        # ask SF if its schedule is ready for EB/Data
        if returnVal is True:
            returnVal = self.sf.clear_to_send_EBs_DATA()

        return returnVal

    # ==== dropping

    def drop_packet(self, packet, reason):

        # log
        self.log(
            SimEngine.SimLog.LOG_PACKET_DROPPED,
            {
                u'_mote_id':  self.id,
                u'packet':    packet,
                u'reason':    reason,
            }
        )

        # remove all the element of packet so it cannot be processed further
        # Note: this is useless, but allows us to catch bugs in case packet is further processed
        for k in list(packet.keys()):
            del packet[k]

    #======================== private =========================================

    def _init_eui64(self, eui64):
        if eui64 is None:
            # generate an EUI-64 based on mote id. The resulting EUI-64 should
            # have U/L bit on
            local_eui64 = netaddr.EUI(u'02-00-00-00-00-00-00-00')
            if self.id == 0:
                # we use a special 40-bit host (extension) value for mote id 0
                # to avoid having all zeros in its IPv6 interface ID
                self.eui64 = netaddr.EUI(local_eui64.value + 0x10000)
            else:
                self.eui64 = netaddr.EUI(local_eui64.value + self.id)
        else:
            self.eui64 = netaddr.EUI(eui64)
        self.log(
            SimEngine.SimLog.LOG_MAC_ADD_ADDR,
            {
                u'_mote_id': self.id,
                u'type'    : self.MAC_ADDR_TYPE_EUI64,
                u'addr'    : str(self.eui64)
            }
        )
        self.log(
            SimEngine.SimLog.LOG_IPV6_ADD_ADDR,
            {
                u'_mote_id': self.id,
                u'type'    : self.IPV6_ADDR_TYPE_LINK_LOCAL,
                u'addr'    : self.get_ipv6_link_local_addr()
            }
        )
