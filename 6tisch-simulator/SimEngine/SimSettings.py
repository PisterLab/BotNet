#!/usr/bin/python
"""
\brief Container for the settings of a simulation run.

\author Thomas Watteyne <thomas.watteyne@inria.fr>
\author Kazushi Muraoka <k-muraoka@eecs.berkeley.edu>
\author Nicola Accettura <nicola.accettura@eecs.berkeley.edu>
\author Xavier Vilajosana <xvilajosana@eecs.berkeley.edu>
"""
from __future__ import division

# =========================== imports =========================================

from builtins import object
import math
import os
import re

# =========================== defines =========================================

# =========================== body ============================================

class SimSettings(object):

    # ==== class attributes / definitions
    DEFAULT_LOG_ROOT_DIR = 'simData'

    # ==== start singleton
    _instance = None
    _init     = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SimSettings, cls).__new__(cls)
        return cls._instance
    # ==== end singleton

    def __init__(
            self,
            cpuID=None,
            run_id=None,
            failIfNotInit=False,
            log_root_dir=DEFAULT_LOG_ROOT_DIR,
            **kwargs
        ):

        if failIfNotInit and not self._init:
            raise EnvironmentError('SimSettings singleton not initialized.')

        # ==== start singleton
        cls = type(self)
        if cls._init:
            return
        cls._init = True
        # ==== end singleton

        try:
            # store params
            self.cpuID                = cpuID
            self.run_id               = run_id
            self.logRootDirectoryPath = os.path.abspath(log_root_dir)

            if kwargs:
                self.__dict__.update(kwargs)
                if self.exec_numSlotframesPerRun and self.exec_minutesPerRun:
                    raise ValueError(
                        'exec_numSlotframesPerRun should be null ' +
                        'when exec_minutesPerRun is used'
                    )
                elif self.exec_minutesPerRun:
                    assert self.exec_numSlotframesPerRun is None
                    # convert "minutes" to "slot
                    self.exec_numSlotframesPerRun = int(
                        math.ceil(
                            self.exec_minutesPerRun *
                            60 /
                            self.tsch_slotDuration /
                            self.tsch_slotframeLength
                        )
                    )
                    # invdalite self.exec_minutesPerRun for the sake
                    # of extract_config_json.py and the exception
                    # handler who generates config.json for
                    # reproduction
                    self.exec_minutesPerRun = None
                elif self.exec_numSlotframesPerRun:
                    assert self.exec_minutesPerRun is None
                    self.exec_numSlotframesPerRun = int(
                        self.exec_numSlotframesPerRun
                    )
                else:
                    raise ValueError(
                        'either exec_numSlotframesPerRun or ' +
                        'exec_minutesPerRun should be specified'
                    )
        except:
            # destroy the singleton
            cls._instance = None
            cls._init = False
            raise

    def setLogDirectory(self, log_directory_name):
        self.logDirectory = log_directory_name

    def setCombinationKeys(self, combinationKeys):
        self.combinationKeys = combinationKeys

    def getOutputFile(self):
        # directory
        dirname = os.path.join(
            self.logRootDirectoryPath,
            self.logDirectory,
            '_'.join(['{0}_{1}'.format(k, getattr(self, k)) for k in self.combinationKeys]),
        )

        # direname could have sub-strings which look like u'...'. This would
        # happen if a combination key is a list having unicode strings. We'll
        # remove the "u" prefixed quotations.
        dirname = re.sub(r"u'(.*?)'", r"\1", dirname)

        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except OSError as e:
                if e.errno == os.errno.EEXIST:
                    # FIXME: handle this race condition properly
                    # Another core/CPU has already made this directory
                    pass
                else:
                    raise

        # file
        if self.cpuID is None:
            tempname = 'output.dat'
        else:
            tempname = 'output_cpu{0}.dat'.format(self.cpuID)
        datafilename = os.path.join(dirname, tempname)

        return datafilename

    def destroy(self):
        cls = type(self)
        cls._instance = None
        cls._init     = False
