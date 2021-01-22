import eel
import gevent
import pytest

import backend.sim
from SimEngine import SimLog


@pytest.fixture(params=['all', ['tsch.add', 'tsch.txdone']])
def log_notification_filter(request):
    return request.param


@pytest.fixture
def log_events():
    # replace eel.notifyLogEvent() with our mock function if it exists
    if hasattr(eel, 'notifyLogEvent'):
        notifyLogEvent_backup = eel.notifyLogEvent
    else:
        notifyLogEvent_backup = None

    _events = []
    eel.notifyLogEvent = lambda logEvent: _events.append(logEvent)
    yield _events

    if notifyLogEvent_backup is None:
        # nothing to do
        pass
    else:
        # put back the original notifyLogEvent to eel
        eel.notifyLogEvent = notifyLogEvent_backup


@pytest.mark.skip
def test_log(log_notification_filter, log_events):
    config = backend.sim.get_default_config()
    settings = config['settings']['regular']
    for key in config['settings']['combination']:
        settings[key] = config['settings']['combination'][key][0]

    # use a short exec_numSlotframesPerRun so that this test ends in a
    # short time
    settings['exec_numSlotframesPerRun'] = 100

    # invoke start()
    sim_greenlet = gevent.spawn(
        backend.sim.start,
        settings,
        log_notification_filter
    )
    gevent.sleep(backend.sim.GEVENT_SLEEP_SECONDS_IN_SIM_ENGINE)
    assert backend.sim._sim_engine is not None

    # find the log file for the simulation
    log_file_path = SimLog.SimLog().log_output_file.name
    assert log_file_path is not None

    # run the simulation until it ends
    gevent.joinall([sim_greenlet])

    # _sim_engine should have gone
    assert backend.sim._sim_engine is None

    if log_notification_filter == 'all':
        # we should have all the log items notified which have been
        # generated during the simulation. to make the test simple, we
        # compare only the number of log events with the number of
        # lines of the log file
        num_log_events = len([
            event for event in log_events
            if event['_type'].startswith('_backend') is False
        ])
        # subtract by one because the very first line of the log file
        # is the 'config' type, that is not recorded through
        # SimLog.log() method.
        num_log_lines = sum(1 for line in open(log_file_path, 'r')) - 1
        assert num_log_events == num_log_lines
    else:
        # only log types specified in the filter can be notified in
        # addition to the default log types which are defined in
        # sim.py
        _filter = (
            log_notification_filter +
            backend.sim.DEFAULT_LOG_NOTIFICATION_FILTER +
            ['_backend.tick.minute'] # special log event for GUI
        )
        _log_types = []
        for event in log_events:
            assert event['_type'] in _filter
            if event['_type'] not in _log_types:
                _log_types.append(event['_type'])

        # we should always have logs of the types specifined by
        # DEFAULT_LOG_NOTIFICATION_FILTER
        for default_log_type in backend.sim.DEFAULT_LOG_NOTIFICATION_FILTER:
            assert default_log_type in _log_types
