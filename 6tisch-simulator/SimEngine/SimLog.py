"""
This module defines the available logs

Usage:
    self.log(
        SimEngine.SimLog.LOG_APP_RX,
        {
            u'_mote_id': self.mote.id,
            u'source':  srcIp.id,
        }
    )
"""
from __future__ import print_function
from __future__ import absolute_import

# ========================== imports =========================================

from builtins import str
from builtins import object
import copy
import json
import traceback

from . import SimSettings

# =========================== defines =========================================

# === simulator
LOG_SIMULATOR_STATE               = {u'type': u'simulator.state',           u'keys': [u'state', u'name']}
LOG_SIMULATOR_RANDOM_SEED         = {u'type': u'simulator.random_seed',     u'keys': [u'value']}

# === packet drops
LOG_PACKET_DROPPED                = {u'type': u'packet_dropped',            u'keys': [u'_mote_id',u'packet',u'reason']}
DROPREASON_NO_ROUTE               = u'no_route'
DROPREASON_TXQUEUE_FULL           = u'txqueue_full'
DROPREASON_NO_TX_CELLS            = u'no_tx_cells'
DROPREASON_MAX_RETRIES            = u'max_retries'
DROPREASON_REASSEMBLY_BUFFER_FULL = u'reassembly_buffer_full'
DROPREASON_VRB_TABLE_FULL         = u'vrb_table_full'
DROPREASON_TIME_EXCEEDED          = u'time_exceeded'
DROPREASON_RANK_ERROR             = u'rank_error'

# === app
LOG_APP_TX                        = {u'type': u'app.tx',                    u'keys': [u'_mote_id',u'packet']}
LOG_APP_RX                        = {u'type': u'app.rx',                    u'keys': [u'_mote_id',u'packet']}

# === secjoin
LOG_SECJOIN_TX                    = {u'type': u'secjoin.tx',                u'keys': [u'_mote_id']}
LOG_SECJOIN_RX                    = {u'type': u'secjoin.rx',                u'keys': [u'_mote_id']}
LOG_SECJOIN_JOINED                = {u'type': u'secjoin.joined',            u'keys': [u'_mote_id']}
LOG_SECJOIN_UNJOINED              = {u'type': u'secjoin.unjoined',          u'keys': [u'_mote_id']}
LOG_SECJOIN_FAILED                = {u'type': u'secjoin.failed',            u'keys': [u'_mote_id']}

# === rpl
LOG_RPL_DIO_TX                    = {u'type': u'rpl.dio.tx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_DIO_RX                    = {u'type': u'rpl.dio.rx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_DAO_TX                    = {u'type': u'rpl.dao.tx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_DAO_RX                    = {u'type': u'rpl.dao.rx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_DIS_TX                    = {u'type': u'rpl.dis.tx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_DIS_RX                    = {u'type': u'rpl.dis.rx',                u'keys': [u'_mote_id',u'packet']}
LOG_RPL_CHURN                     = {u'type': u'rpl.churn',                 u'keys': [u'_mote_id',u'rank',u'preferredParent']}
LOG_RPL_LOCAL_REPAIR              = {u'type': u'rpl.local_repair',          u'keys': [u'_mote_id']}

# === 6LoWPAN
LOG_SIXLOWPAN_PKT_TX              = {u'type': u'sixlowpan.pkt.tx',          u'keys': [u'_mote_id',u'packet']}
LOG_SIXLOWPAN_PKT_FWD             = {u'type': u'sixlowpan.pkt.fwd',         u'keys': [u'_mote_id',u'packet']}
LOG_SIXLOWPAN_PKT_RX              = {u'type': u'sixlowpan.pkt.rx',          u'keys': [u'_mote_id',u'packet']}
LOG_SIXLOWPAN_FRAG_GEN            = {u'type': u'sixlowpan.frag.gen',        u'keys': [u'_mote_id',u'packet']}

# === MSF
LOG_MSF_TX_CELL_UTILIZATION       = {u'type': u'msf.tx_cell_utilization',   u'keys': [u'_mote_id',u'neighbor',u'value']}
LOG_MSF_RX_CELL_UTILIZATION       = {u'type': u'msf.rx_cell_utilization',   u'keys': [u'_mote_id',u'neighbor',u'value']}
LOG_MSF_ERROR_SCHEDULE_FULL       = {u'type': u'msf.error.schedule_full',   u'keys': [u'_mote_id']}

# === sixp
LOG_SIXP_TX                       = {u'type': u'sixp.tx',                   u'keys': [u'_mote_id',u'packet']}
LOG_SIXP_RX                       = {u'type': u'sixp.rx',                   u'keys': [u'_mote_id',u'packet']}
LOG_SIXP_TRANSACTION_COMPLETED    = {u'type': u'sixp.comp',                 u'keys': [u'_mote_id',u'peerMac',u'seqNum', u'cmd']}
LOG_SIXP_TRANSACTION_TIMEOUT      = {u'type': u'sixp.timeout',              u'keys': [u'_mote_id',u'srcMac',u'dstMac',u'seqNum', u'cmd']}
LOG_SIXP_TRANSACTION_ABORTED      = {u'type': u'sixp.abort',                u'keys': [u'_mote_id',u'srcMac',u'dstMac',u'seqNum', u'cmd']}

# === tsch
LOG_TSCH_SYNCED                   = {u'type': u'tsch.synced',               u'keys': [u'_mote_id']}
LOG_TSCH_DESYNCED                 = {u'type': u'tsch.desynced',             u'keys': [u'_mote_id']}
LOG_TSCH_EB_TX                    = {u'type': u'tsch.eb.tx',                u'keys': [u'_mote_id',u'packet']}
LOG_TSCH_EB_RX                    = {u'type': u'tsch.eb.rx',                u'keys': [u'_mote_id',u'packet']}
LOG_TSCH_ADD_CELL                 = {u'type': u'tsch.add_cell',             u'keys': [u'_mote_id',u'slotFrameHandle',u'slotOffset',u'channelOffset',u'neighbor',u'cellOptions']}
LOG_TSCH_DELETE_CELL              = {u'type': u'tsch.delete_cell',          u'keys': [u'_mote_id',u'slotFrameHandle',u'slotOffset',u'channelOffset',u'neighbor',u'cellOptions']}
LOG_TSCH_TXDONE                   = {u'type': u'tsch.txdone',               u'keys': [u'_mote_id',u'channel',u'slot_offset', u'channel_offset', u'packet',u'isACKed']}
LOG_TSCH_RXDONE                   = {u'type': u'tsch.rxdone',               u'keys': [u'_mote_id',u'channel',u'slot_offset', u'channel_offset', u'packet']}
LOG_TSCH_BACKOFF_EXPONENT_UPDATED = {u'type': u'tsch.be.updated',           u'keys': [u'_mote_id',u'old_be', u'new_be']}
LOG_TSCH_ADD_SLOTFRAME            = {u'type': u'tsch.add_slotframe',        u'keys': [u'_mote_id',u'slotFrameHandle',u'length']}
LOG_TSCH_DELETE_SLOTFRAME         = {u'type': u'tsch.delete_slotframe',     u'keys': [u'_mote_id',u'slotFrameHandle',u'length']}

# === mote info
LOG_RADIO_STATS                   = {u'type': u'radio.stats',               u'keys': [u'_mote_id', u'idle_listen', u'tx_data_rx_ack', u'tx_data', u'rx_data_tx_ack', u'rx_data', u'sleep']}
LOG_MAC_ADD_ADDR                  = {u'type': u'mac.add_addr',              u'keys': [u'_mote_id', u'type', u'addr']}
LOG_IPV6_ADD_ADDR                 = {u'type': u'ipv6.add_addr',             u'keys': [u'_mote_id', u'type', u'addr']}

# === propagation
LOG_PROP_TRANSMISSION             = {u'type': u'prop.transmission',         u'keys': [u'channel',u'packet']}
LOG_PROP_INTERFERENCE             = {u'type': u'prop.interference',         u'keys': [u'_mote_id',u'channel',u'lockon_transmission',u'interfering_transmissions']}
LOG_PROP_DROP_LOCKON              = {u'type': u'prop.drop_lockon' ,         u'keys': [u'_mote_id',u'channel',u'lockon_transmission']}

# === connectivity matrix
LOG_CONN_MATRIX_K7_UPDATE         = {u'type': u'conn.matrix.update',        u'keys': [u'start_trace_position', u'end_trace_position', u'asn_of_next_update']}

# ============================ SimLog =========================================

class SimLog(object):

    # ==== start singleton
    _instance      = None
    _init          = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SimLog, cls).__new__(cls)
        return cls._instance
    # ==== end singleton

    def __init__(self, failIfNotInit=False):

        if failIfNotInit and not self._init:
            raise EnvironmentError(u'SimLog singleton not initialized.')

        # ==== start singleton
        cls = type(self)
        if cls._init:
            return
        cls._init = True
        # ==== end singleton

        try:
            # get singletons
            self.settings   = SimSettings.SimSettings()
            self.engine     = None # will be defined by set_simengine

            # local variables
            self.log_filters = []

            # open log file
            self.log_output_file = open(self.settings.getOutputFile(), u'a')

            # write config to log file; if a file with the same file name exists,
            # append logs to the file. this happens if you multiple runs on the
            # same CPU. And amend config line; config line in log file should have
            # '_type' field. And 'run_id' type should be '_run_id'
            config_line = copy.deepcopy(self.settings.__dict__)
            config_line[u'_type']   = u'config'
            config_line[u'_run_id'] = config_line[u'run_id']
            del config_line[u'run_id']
            json_string = json.dumps(config_line)
            self.log_output_file.write(json_string + u'\n')
        except:
            # destroy the singleton
            cls._instance = None
            cls._init = False
            raise

    def log(self, simlog, content):
        """
        :param dict simlog:
        :param dict content:
        """

        # ignore types that are not listed in the simulation config
        if (self.log_filters != u'all') and (simlog[u'type'] not in self.log_filters):
            return

        # if a key is passed but is not listed in the log definition, raise error
        if (u'keys' in simlog) and (sorted(simlog[u'keys']) != sorted(content.keys())):
            raise Exception(
                "Wrong keys passed to log() function for type {0}!\n    - expected {1}\n    - got      {2}".format(
                    simlog[u'type'],
                    sorted(simlog[u'keys']),
                    sorted(content.keys()),
                )
            )

        # if self.engine is not available, consider the current time
        # is ASN 0.
        if self.engine is None:
            asn = 0
        else:
            asn = self.engine.asn

        # update the log content
        content.update(
            {
                "_asn":       asn,
                "_type":      simlog["type"],
                "_run_id":    self.settings.run_id
            }
        )

        # write line
        try:
            json_string = json.dumps(content, sort_keys=True)
            self.log_output_file.write(json_string + u'\n')
        except Exception as err:
            output  = []
            output += [u'----------------------']
            output += [u'']
            output += [u'log() FAILED for content']
            output += [str(content)]
            output += [u'']
            output += [str(err)]
            output += [u'']
            output += [traceback.format_exc(err)]
            output += [u'']
            output += [u'----------------------']
            output  = u'\n'.join(output)
            print(output)
            raise

    def flush(self):
        # flush the internal buffer, write data to the file
        assert not self.log_output_file.closed
        self.log_output_file.flush()

    def set_simengine(self, engine):
        self.engine = engine

    def set_log_filters(self, log_filters):
        self.log_filters = log_filters

    def destroy(self):
        # close log file
        if not self.log_output_file.closed:
            self.log_output_file.close()

        cls = type(self)
        cls._instance       = None
        cls._init           = False

    # ============================== private ==================================
