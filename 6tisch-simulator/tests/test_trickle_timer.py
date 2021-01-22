from __future__ import absolute_import
from builtins import range
import pytest

from . import test_utils as u
from SimEngine.Mote.trickle_timer import TrickleTimer

# use the default values defined in RFC 6550
DEFAULT_DIO_INTERVAL_MIN = 3
DEFAULT_DIO_INTERVAL_DOUBLINGS = 20
DEFAULT_DIO_REDUNDANCY_CONSTANT = 10
Imin = pow(2, DEFAULT_DIO_INTERVAL_MIN) # msec
Imax = DEFAULT_DIO_INTERVAL_DOUBLINGS
K    = DEFAULT_DIO_REDUNDANCY_CONSTANT


def test_initial_state(sim_engine):
    sim_engine = sim_engine()

    def _callback():
        pass

    trickle_timer = TrickleTimer(Imin, Imax, K, _callback)

    assert trickle_timer.min_interval == Imin
    assert trickle_timer.max_interval == Imin * pow(2, Imax)
    assert trickle_timer.redundancy_constant == K
    assert trickle_timer.user_callback == _callback


@pytest.fixture(params=list(range(15)))
def num_consistency(request):
    return request.param


def test_redundancy_constant(sim_engine, num_consistency):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )

    result = {'is_callback_called': False}

    def _callback():
        result['is_callback_called'] = True

    trickle_timer = TrickleTimer(Imin, Imax, K, _callback)
    # set one slotframe long to the interval (for test purpose)
    INITIAL_INTERVAL = 1010 # ms
    trickle_timer.start()
    trickle_timer.interval = INITIAL_INTERVAL
    trickle_timer._start_next_interval()

    for _ in range(num_consistency):
        trickle_timer.increment_counter()

    u.run_until_asn(sim_engine, sim_engine.settings.tsch_slotframeLength)

    if num_consistency < K:
        assert result['is_callback_called'] == True
    else:
        assert result['is_callback_called'] == False
    assert trickle_timer.interval == INITIAL_INTERVAL * 2


def test_interval_doubling(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )

    def _callback():
        pass

    one_slotframe = sim_engine.settings.tsch_slotframeLength
    i_min = 1000
    i_max = 2

    trickle_timer = TrickleTimer(i_min, i_max, K, _callback)
    # set one slotframe long to the interval manually (for test purpose)
    INITIAL_INTERVAL = 1010 # ms
    trickle_timer.start()
    trickle_timer.interval = INITIAL_INTERVAL
    trickle_timer._start_next_interval()

    assert trickle_timer.interval == INITIAL_INTERVAL

    # interval should be doubled
    u.run_until_asn(sim_engine, sim_engine.getAsn() + one_slotframe)
    assert trickle_timer.interval == INITIAL_INTERVAL * 2

    # doubled interval will exceed the maximum interval. then, the resulting
    # interval should be the maximum value
    u.run_until_asn(sim_engine, sim_engine.getAsn() + one_slotframe * 2)
    assert trickle_timer.interval == i_min * pow(2, i_max)


def test_reset(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )

    def _callback():
        pass

    trickle_timer = TrickleTimer(Imin, Imax, K, _callback)
    trickle_timer.start()

    # get ASN of 't' and one of the end of the interval
    original_event_at_t = sim_engine.uniqueTagSchedule[trickle_timer.unique_tag_base + '_at_t']
    original_event_at_end_of_interval = sim_engine.uniqueTagSchedule[trickle_timer.unique_tag_base + '_at_i']

    u.run_until_asn(sim_engine, sim_engine.getAsn() + 1)

    # reset the timer
    trickle_timer.reset()

    # interval should be the minimum value by reset()
    assert trickle_timer.interval == Imin
    # events should be re-scheduled accordingly

    assert original_event_at_t is not sim_engine.uniqueTagSchedule[trickle_timer.unique_tag_base + '_at_t']
    assert original_event_at_end_of_interval is not sim_engine.uniqueTagSchedule[trickle_timer.unique_tag_base + '_at_i']


def test_stop(sim_engine):
    sim_engine = sim_engine(
        diff_config = {
            'exec_numMotes': 1
        }
    )

    def _callback():
        pass

    # remove all the scheduled events
    sim_engine.events = {}
    trickle_timer = TrickleTimer(Imin, Imax, K, _callback)
    trickle_timer.start()
    assert len(list(sim_engine.events.keys())) == 2
    trickle_timer.stop()
    assert len(list(sim_engine.events.keys())) == 0
