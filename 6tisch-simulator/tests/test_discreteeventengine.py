from __future__ import absolute_import
from builtins import range
from builtins import object
from SimEngine import SimEngine
import SimEngine.Mote.MoteDefines as d
from . import test_utils as u

'''
def test_create_destroy_engine(repeat4times):
    engine = SimEngine.DiscreteEventEngine()
    print id(engine)
    engine.destroy()
'''
def test_create_start_destroy_engine(repeat4times):
    engine = SimEngine.DiscreteEventEngine()
    engine.start()
    engine.join()

class StateOfTest(object):
    def __init__(self):
        self.events = []
    def _cb_asn_1_1(self):
        self.events += ['1.1']
    def _cb_asn_1_2(self):
        self.events += ['1.2']
    def _cb_asn_2_0(self):
        self.events += ['2.0']

def test_event_execution_order(repeat4times):

    # create engine
    engine = SimEngine.DiscreteEventEngine()
    engine.scheduleAtAsn(
        asn             = 10,
        cb              = engine._actionEndSim,
        uniqueTag       = ('engine','_actionEndSim'),
        intraSlotOrder  = 3,
    )
    stateoftest = StateOfTest()

    # schedule events (out of order)
    engine.scheduleAtAsn(
        asn             = 1,
        cb              = stateoftest._cb_asn_1_1,
        uniqueTag       = ('stateoftest','_cb_asn_1_1'),
        intraSlotOrder  = 1,
    )
    engine.scheduleAtAsn(
        asn             = 2,
        cb              = stateoftest._cb_asn_2_0,
        uniqueTag       = ('stateoftest','_cb_asn_2_0'),
        intraSlotOrder  = 0,
    )
    engine.scheduleAtAsn(
        asn             = 1,
        cb              = stateoftest._cb_asn_1_2,
        uniqueTag       = ('stateoftest','_cb_asn_1_2'),
        intraSlotOrder  = 2,
    )

    # run engine, run until done
    assert not engine.is_alive()
    engine.start()
    engine.join()
    assert not engine.is_alive()

    # verify we got the right events
    assert stateoftest.events == ['1.1','1.2','2.0']

def test_event_order_at_same_asn():
    # if we have multiple events scheduled at the same ASN with the
    # same intraSlotOrder, their callbacks should be executed in order
    # of insertion (FIFO)

    INTRA_SLOT_ORDER = d.INTRASLOTORDER_STACKTASKS
    NUM_TEST_RUNS = 1000
    result = []

    def _callback_1():
        result.append(1)

    def _callback_2():
        result.append(2)

    def _callback_3():
        result.append(3)

    for _ in range(NUM_TEST_RUNS):
        result = []
        engine = SimEngine.DiscreteEventEngine()

        # schedule events at ASN 1
        engine.scheduleAtAsn(1, _callback_1, 'first_event', INTRA_SLOT_ORDER)
        engine.scheduleAtAsn(1, _callback_2, 'second_event', INTRA_SLOT_ORDER)
        engine.scheduleAtAsn(1, _callback_3, 'third_event', INTRA_SLOT_ORDER)

        engine.start()
        engine.join()

        assert result == [1, 2, 3]
