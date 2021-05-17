"""
\brief Discrete-event simulation engine.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

# ========================== imports =========================================

from builtins import zip
from builtins import str
from builtins import range
from past.utils import old_div
from collections import OrderedDict
import hashlib
import platform
import random
import sys
import threading
import time
import traceback
import json

from . import Mote
from . import SimSettings
from . import SimLog
from . import Connectivity
from . import SimConfig

# special SwarmSim import
# insert at 1, 0 is the script path (or '' in REPL)
import os
SIMENGINE_ROOT_PATH = os.path.dirname(__file__)
SWARM_SIM_MASTER_PATH = os.path.join(
    SIMENGINE_ROOT_PATH,
    '../../swarmsimmaster'
)
sys.path.insert(1, SWARM_SIM_MASTER_PATH)
import comms_env
import rpyc
import numpy as np

import inspect
# =========================== defines =========================================

# =========================== body ============================================


class DiscreteEventEngine(threading.Thread):

    #===== start singleton
    _instance      = None
    _init          = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DiscreteEventEngine,cls).__new__(cls)
        return cls._instance
    #===== end singleton

    def __init__(self, cpuID=None, run_id=None, verbose=True):
        #===== singleton
        cls = type(self)
        if cls._init:
            return
        cls._init = True
        #===== singleton

        try:
            # store params
            self.cpuID                          = cpuID
            self.run_id                         = run_id
            self.verbose                        = verbose

            # local variables
            self.dataLock                       = threading.RLock()
            self.pauseSem                       = threading.Semaphore(0)
            self.simPaused                      = False
            self.goOn                           = True
            self.asn                            = 0
            self.exc                            = None
            self.events                         = {}
            self.uniqueTagSchedule              = {}
            self.random_seed                    = None
            self._init_additional_local_variables()

            self.max_diff = 0
            self.diff = 1e-69

            # initialize parent class
            threading.Thread.__init__(self)
            self.name                           = u'DiscreteEventEngine'
        except:
            # an exception happened when initializing the instance

            # destroy the singleton
            cls._instance         = None
            cls._init             = False
            raise

    def destroy(self):
        cls = type(self)
        if cls._init:
            # initialization finished without exception

            if self.is_alive():
                # thread is start'ed
                self.play()           # cause one more loop in thread
                self._actionEndSim()  # causes self.gOn to be set to False
                self.join()           # wait until thread is dead
            else:
                # thread NOT start'ed yet, or crashed

                # destroy the singleton
                cls._instance         = None
                cls._init             = False
        else:
            # initialization failed
            pass # do nothing, singleton already destroyed

    #======================== thread ==========================================

    def run(self):
        """ loop through events """
        try:
            # additional routine
            self._routine_thread_started()

            self.initialized_network = False

            # consume events until self.goOn is False
            while self.goOn:
                # tell robotic simulator to run for 1 ASN
                if self.settings.robot_sim_enabled:
                    self._robo_sim_loop()
                with self.dataLock:

                    # abort simulation when no more events
                    if not self.events:
                        break

                    # update the current ASN
                    self.asn += 1
                    # if self.networkFormed and not self.initialized_network:
                    #     self.asn = 0
                    #     self.initialized_network = True

                    # perform any inter-simulator synchronization
                    if self.settings.robot_sim_enabled:
                        self._robo_sim_sync()

                    if self.asn not in self.events:
                        continue

                    intraSlotOrderKeys = list(self.events[self.asn].keys())
                    intraSlotOrderKeys.sort()

                    cbs = []
                    for intraSlotOrder in intraSlotOrderKeys:
                        for uniqueTag, cb in list(self.events[self.asn][intraSlotOrder].items()):
                            # if uniqueTag == "recvTag": populate rcving_mote neighbor pose table # TODO: figure this out as abstract call
                            cbs += [cb]
                            del self.uniqueTagSchedule[uniqueTag]
                    del self.events[self.asn]

                # call the callbacks (outside the dataLock)
                for cb in cbs:
                    cb()
                    # if rcv_cb: update rcving_mote neighbor pose table

                if self.settings.robot_sim_enabled:
                    self._robo_sim_update()

        except Exception as e:
            # thread crashed

            # record the exception
            self.exc = e

            # additional routine
            self._routine_thread_crashed()

            # print
            output  = []
            output += [u'']
            output += [u'==============================']
            output += [u'']
            output += [u'CRASH in {0}!'.format(self.name)]
            output += [u'']
            output += [traceback.format_exc()]
            output += [u'==============================']
            output += [u'']
            output += [u'The current ASN is {0}'.format(self.asn)]
            output += [u'The log file is {0}'.format(
                self.settings.getOutputFile()
            )]
            output += [u'']
            output += [u'==============================']
            output += [u'6tisch.json to reproduce:']
            output += [u'']
            output += [u'']
            output  = u'\n'.join(output)
            output += json.dumps(
                SimConfig.SimConfig.generate_config(
                    settings_dict = self.settings.__dict__,
                    random_seed   = self.random_seed
                ),
                indent = 4
            )
            output += u'\n\n==============================\n'

            sys.stderr.write(output)

            # flush all the buffered log data
            SimLog.SimLog().flush()

        else:
            # thread ended (gracefully)

            # no exception
            self.exc = None

            # additional routine
            self._routine_thread_ended()

        finally:

            # destroy this singleton
            cls = type(self)
            cls._instance                      = None
            cls._init                          = False

    def join(self):
        super(DiscreteEventEngine, self).join()
        if self.exc:
            raise self.exc

    #======================== public ==========================================

    # === getters/setters

    def getAsn(self):
        return self.asn

    #=== scheduling

    def scheduleAtAsn(self, asn, cb, uniqueTag, intraSlotOrder):
        """
        Schedule an event at a particular ASN in the future.
        Also removed all future events with the same uniqueTag.
        """

        # make sure we are scheduling in the future
        assert asn > self.asn

        # remove all events with same uniqueTag (the event will be rescheduled)
        self.removeFutureEvent(uniqueTag)

        with self.dataLock:

            if asn not in self.events:
                self.events[asn] = {
                    intraSlotOrder: OrderedDict([(uniqueTag, cb)])
                }

            elif intraSlotOrder not in self.events[asn]:
                self.events[asn][intraSlotOrder] = (
                    OrderedDict([(uniqueTag, cb)])
                )

            elif uniqueTag not in self.events[asn][intraSlotOrder]:
                self.events[asn][intraSlotOrder][uniqueTag] = cb

            else:
                self.events[asn][intraSlotOrder][uniqueTag] = cb

            self.uniqueTagSchedule[uniqueTag] = (asn, intraSlotOrder)

    def scheduleIn(self, delay, cb, uniqueTag, intraSlotOrder):
        """
        Schedule an event 'delay' seconds into the future.
        Also removed all future events with the same uniqueTag.
        """

        with self.dataLock:
            asn = int(self.asn + (float(delay) / float(self.settings.tsch_slotDuration)))

            self.scheduleAtAsn(asn, cb, uniqueTag, intraSlotOrder)

    # === play/pause

    def play(self):
        self._actionResumeSim()

    def pauseAtAsn(self,asn):
        self.scheduleAtAsn(
            asn              = asn,
            cb               = self._actionPauseSim,
            uniqueTag        = (u'DiscreteEventEngine', u'_actionPauseSim'),
            intraSlotOrder   = Mote.MoteDefines.INTRASLOTORDER_ADMINTASKS,
        )

    # === misc

    def is_scheduled(self, uniqueTag):
        with self.dataLock:
            return uniqueTag in self.uniqueTagSchedule

    def removeFutureEvent(self, uniqueTag):
        with self.dataLock:
            if uniqueTag not in self.uniqueTagSchedule:
                # new event, not need to delete old instances
                return

            # get old instances occurences
            (asn, intraSlotOrder) = self.uniqueTagSchedule[uniqueTag]

            # make sure it's in the future
            assert asn >= self.asn

            # delete it
            del self.uniqueTagSchedule[uniqueTag]
            del self.events[asn][intraSlotOrder][uniqueTag]

            # and cleanup event structure if it's empty
            if not self.events[asn][intraSlotOrder]:
                del self.events[asn][intraSlotOrder]

            if not self.events[asn]:
                del self.events[asn]

    def terminateSimulation(self,delay):
        with self.dataLock:
            self.asnEndExperiment = self.asn+delay
            self.scheduleAtAsn(
                    asn                = self.asn+delay,
                    cb                 = self._actionEndSim,
                    uniqueTag          = (u'DiscreteEventEngine', u'_actionEndSim'),
                    intraSlotOrder     = Mote.MoteDefines.INTRASLOTORDER_ADMINTASKS,
            )

    # ======================== private ========================================

    def _actionPauseSim(self):
        assert self.simPaused==False
        self.simPaused = True
        self.pauseSem.acquire()

    def _actionResumeSim(self):
        if self.simPaused:
            self.simPaused = False
            self.pauseSem.release()

    def _actionEndSim(self):
        with self.dataLock:
            self.goOn = False

    def _actionEndSlotframe(self):
        """Called at each end of slotframe_iteration."""

        slotframe_iteration = int(old_div(self.asn, self.settings.tsch_slotframeLength))

        # print
        if self.verbose:

            # NOTE: DO NOT DELETE, SIM BREAKS
            if self.max_diff < self.diff:
                self.max_diff = self.diff
            if slotframe_iteration % 100 == 0:
                print(u'   slotframe_iteration: {0}/{1}'.format(slotframe_iteration, self.settings.exec_numSlotframesPerRun-1))

        # schedule next statistics collection
        self.scheduleAtAsn(
            asn              = self.asn + self.settings.tsch_slotframeLength,
            cb               = self._actionEndSlotframe,
            uniqueTag        = (u'DiscreteEventEngine', u'_actionEndSlotframe'),
            intraSlotOrder   = Mote.MoteDefines.INTRASLOTORDER_ADMINTASKS,
        )

    # ======================== abstract =======================================

    def _init_additional_local_variables(self):
        pass

    def _routine_thread_started(self):
        pass

    def _routine_thread_crashed(self):
        pass

    def _routine_thread_ended(self):
        pass

    # ======================= Robotic Simulator Abstract ===============================

    def _robo_sim_loop(self, steps=1):
        pass

    def _robo_sim_sync(self):
        pass

    def _robo_sim_update(self):
        pass


class SimEngine(DiscreteEventEngine):

    DAGROOT_ID = 0

    def _init_additional_local_variables(self):
        self.settings                   = SimSettings.SimSettings()

        if self.settings.rrsf_slotframe_len is False:
            self.settings.rrsf_slotframe_len = self.settings.exec_numMotes
            self.settings.tsch_slotframeLength = self.settings.exec_numMotes

        # set random seed
        if   self.settings.exec_randomSeed == u'random':
            self.random_seed = random.randint(0, sys.maxsize)
        elif self.settings.exec_randomSeed == u'context':
            # with context for exec_randomSeed, an MD5 value of
            # 'startTime-hostname-run_id' is used for a random seed
            startTime = SimConfig.SimConfig.get_startTime()
            if startTime is None:
                startTime = time.time()
            context = (platform.uname()[1], str(startTime), str(self.run_id))
            md5 = hashlib.md5()
            md5.update(u'-'.join(context).encode('utf-8'))
            self.random_seed = int(md5.hexdigest(), 16) % sys.maxsize
        else:
            assert isinstance(self.settings.exec_randomSeed, int)
            self.random_seed = self.settings.exec_randomSeed
        # apply the random seed; log the seed after self.log is initialized
        random.seed(a=self.random_seed)
        np.random.seed(self.random_seed)

        if self.settings.motes_eui64:
            eui64_table = self.settings.motes_eui64[:]
            if len(eui64_table) < self.settings.exec_numMotes:
                eui64_table.extend(
                    [None] * (self.settings.exec_numMotes - len(eui64_table))
                )
        else:
            eui64_table = [None] * self.settings.exec_numMotes

        self.motes = [
            Mote.Mote.Mote(id, eui64)
            for id, eui64 in zip(
                    list(range(self.settings.exec_numMotes)),
                    eui64_table
            )
        ]

        print(f"{len(self.motes)} MOTES: {[m.id for m in self.motes]}")

        eui64_list = set([mote.get_mac_addr() for mote in self.motes])
        if len(eui64_list) != len(self.motes):
            assert len(eui64_list) < len(self.motes)
            raise ValueError(u'given motes_eui64 causes duplicates')

        # SwarmSim, TODO: this will be an RPC call implemented by the socket recipent
        # TODO: perform exchange of ASN information for SwarmSim timesteps
        # TODO: scale velocities accordingly, not terribly important right now

        self.networkFormed              = False


        self._init_controls_update()


        self.rpc = self.settings.dual_vis 

        if self.settings.robot_sim_enabled:
            timestep = self.settings.tsch_slotDuration
            if not self.settings.collision_modelling:
                timestep *= self.control_update_period

            if self.rpc:
                self.robot_sim                  =  rpyc.connect("localhost", 18861, config={'allow_public_attrs': True, 'allow_all_attrs': True, 'allow_pickle': True}).root
                net_configs = {
                    'follow': self.settings.follow,
                    'flock_rad': self.settings.flock_rad,
                    'flock_vel': self.settings.flock_vel,
                    'seed': self.random_seed
                }
                self.robot_sim.initialize_simulation(net_configs, num_agents = self.settings.exec_numMotes, timestep=timestep, seed=self.random_seed, update_period=self.control_update_period)
                #self.robot_sim.initialize_simulation(goons=robotCoords, timestep=timestep,
                                                     #seed=self.random_seed, update_period=self.control_update_period)
                #wait for simulation to process
                self.robot_sim.set_sync(False)
                while not self.robot_sim.synced():
                    continue
                self.robot_sim.set_mote_key_map({})
            else:

                self.robot_sim                  = comms_env.SwarmSimCommsEnv(self.settings, num_agents = self.settings.exec_numMotes,
                                                                         timestep=timestep,
                                                                         seed=self.random_seed,
                                                                         update_period=self.control_update_period
                                                                         )
                self.robot_sim.mote_key_map     = {}

            moteStates = self.robot_sim.get_all_mote_states()
            if self.rpc:
                newMap = {}
            for i, robot_mote_id in enumerate(moteStates.keys()):
                mote = self.motes[i]
                if not self.rpc:
                    self.robot_sim.mote_key_map[mote.id] = robot_mote_id
                else:
                    newMap[mote.id] = robot_mote_id
                mote.setLocation(*(moteStates[robot_mote_id][:2]))
                mote.console_log(mote.getLocation())

            if self.rpc:
                self.robot_sim.set_mote_key_map(newMap, inv=True)
            else:
                self.robot_sim.mote_key_inv_map = dict((v, k) for k, v in self.robot_sim.mote_key_map.items())
        else:
            for i, coord in enumerate(robotCoords):
                mote = self.motes[i]
                mote.setLocation(*(coord[:2]))

        self.connectivity               = Connectivity.Connectivity(self)
        self.log                        = SimLog.SimLog().log
        SimLog.SimLog().set_simengine(self)

        # log the random seed
        self.log(
            SimLog.LOG_SIMULATOR_RANDOM_SEED,
            {
                u'value': self.random_seed
            }
        )
        # flush buffered logs, which are supposed to be 'config' and
        # 'random_seed' lines, right now. This could help, for instance, when a
        # simulation is stuck by an infinite loop without writing these
        # 'config' and 'random_seed' to a log file.
        SimLog.SimLog().flush()

        # select dagRoot
        self.motes[self.DAGROOT_ID].setDagRoot()

        # boot all motes
        for i in range(len(self.motes)):
            self.motes[i].boot()
            self.motes[i].console_log(f"IPv6 addr: {self.motes[i].get_ipv6_global_addr()}")

        print("Completed SimEngine Init.")

    def _routine_thread_started(self):
        # log
        self.log(
            SimLog.LOG_SIMULATOR_STATE,
            {
                u'name':   self.name,
                u'state':  u'started'
            }
        )

        # schedule end of simulation
        self.scheduleAtAsn(
            asn              = self.settings.tsch_slotframeLength*self.settings.exec_numSlotframesPerRun,
            cb               = self._actionEndSim,
            uniqueTag        = (u'SimEngine',u'_actionEndSim'),
            intraSlotOrder   = Mote.MoteDefines.INTRASLOTORDER_ADMINTASKS,
        )
        print(f'slotframe len : {self.settings.tsch_slotframeLength}')

        # schedule action at every end of slotframe_iteration
        self.scheduleAtAsn(
            asn              = self.asn + self.settings.tsch_slotframeLength - 1,
            cb               = self._actionEndSlotframe,
            uniqueTag        = (u'SimEngine', u'_actionEndSlotframe'),
            intraSlotOrder   = Mote.MoteDefines.INTRASLOTORDER_ADMINTASKS,
        )

    def _routine_thread_crashed(self):
        # log
        self.log(
            SimLog.LOG_SIMULATOR_STATE,
            {
                "name": self.name,
                "state": "crash"
            }
        )

    def _routine_thread_ended(self):
        # log
        self.log(
            SimLog.LOG_SIMULATOR_STATE,
            {
                "name": self.name,
                "state": "stopped"
            }
        )

    def get_mote_by_mac_addr(self, mac_addr):
        for mote in self.motes:
            if mote.is_my_mac_addr(mac_addr):
                return mote
        return None

    def get_mote_by_id(self, mote_id):
        # there must be a mote having mote_id. otherwise, the following line
        # raises an exception.
        return [mote for mote in self.motes if mote.id == mote_id][0]

    # ============== Robot Simulator Initialization ===================

    

    def _init_controls_update(self):
        update_mode = self.settings.control_update_mode
        if update_mode == "Slotframe":
            self.control_update_period = self.settings.rrsf_slotframe_len
        elif update_mode == "Slot":
            self.control_update_period = self.settings.control_update_period_slots
        elif update_mode == "Hz":
            self.control_update_period = int(1 / (self.settings.control_update_rate_hz * self.settings.tsch_slotDuration))

    # ============== Robot Simulator Communication ====================

    def _robo_sim_loop(self): # NOTE: collision modelling should likely be higher update rate
        if not self.networkFormed:
            return

        relative_asn = self.asn - (self.networkFormedTime + self.control_update_period)
        if not self.settings.collision_modelling and relative_asn % self.control_update_period != 0:
            return

        self.robot_sim.main_loop()

        if self.rpc:
            self.robot_sim.set_sync(False)

            while not self.robot_sim.synced():
                continue



    def _robo_sim_sync(self):
        networkStartSwitch = True

        states = self.robot_sim.get_all_mote_states()
        for mote in self.motes:
            mote.setLocation(*(states[self.robot_sim.get_mote_key_map()[mote.id]][:2]))
            networkStartSwitch = networkStartSwitch and mote.isBroadcasting

        self.connectivity.matrix.update()

        if not self.networkFormed and networkStartSwitch:
            print(f"NETWORK FORMED AT {self.getAsn()}")
            self.networkFormedTime = self.getAsn()

        self.networkFormed = self.networkFormed or networkStartSwitch

    def _robo_sim_update(self):
        if not self.networkFormed:
            return

        relative_asn = self.asn - (self.networkFormedTime + self.control_update_period)
        if relative_asn <= 0 or relative_asn % self.control_update_period != 0:
            return

        agent_neighbor_table = []
        for agent in self.motes:
            agent.console_log(agent.neighbors)
            agent_neighbor_table.append((agent.id, agent.neighbors))
            agent.neighbors = {} # flush neighbors

        self.robot_sim.set_all_mote_neighbors(agent_neighbor_table)
