import json
import gzip
import os
import subprocess

import eel
import gevent
import pytest

import backend
import backend.sim
import backend.utils


def call_exposed_api(func, *args):
    if func == backend.sim.start:
        gevent.spawn(func, *args)
    else:
        func(*args)
    # yield the CPU so that the func is invoked in a greenlet
    gevent.sleep(backend.sim.GEVENT_SLEEP_SECONDS_IN_SIM_ENGINE)


@pytest.fixture(scope='module', autouse=True)
def setup_default_config_json():
    backend.utils.create_config_json()
    yield
    backend.utils._delete_config_json()


@pytest.fixture(scope='module', autouse=True)
def setup_fake_notifyLogEvent(request):
    if hasattr(eel, 'notifyLogEvent'):
        notifyLogEvent_backup = eel.notifyLogEvent
    else:
        notifyLogEvent_backup = None
    eel.notifyLogEvent = lambda event: None

    def _revert_notifyLogEvent():
        if notifyLogEvent_backup is None:
            # nothing to do
            pass
        else:
            eel.notifyLogEvent = notifyLogEvent_backup

    request.addfinalizer(_revert_notifyLogEvent)


@pytest.fixture
def sim_engine():
    def _generator(settings):
        call_exposed_api(backend.sim.start, settings)
        return backend.sim._sim_engine

    yield _generator
    if backend.sim._sim_engine is not None:
        backend.sim._restore_stderr()
        backend.sim._destroy_sim()


@pytest.fixture
def default_config():
    # read the default config.json from the simulator source directory
    default_config_path = os.path.join(
        backend.get_simulator_path(),
        'bin/config.json'
    )
    with open(default_config_path) as f:
        default_config = json.load(f)
    return default_config


@pytest.fixture
def default_settings(default_config):
    settings = default_config['settings']['regular']
    for key in list(default_config['settings']['combination'].keys()):
        settings[key] = default_config['settings']['combination'][key][0]
    return settings


def test_get_default_config(default_config):
    config = backend.sim.get_default_config()
    assert config['version'] == 0
    assert config['settings'] == default_config['settings']
    assert config['execution'] == {
        "numCPUs": 1,
        "numRuns": 1
    }
    assert config['logging'] == 'all'
    assert config['log_directory_name'] == 'startTime'
    assert config['post'] == []


@pytest.fixture(params=['success', 'failure'])
def fixture_test_put_default_config_type(request):
    return request.param


def test_put_default_config(
        default_config,
        fixture_test_put_default_config_type
    ):

    if fixture_test_put_default_config_type == 'success':
        # change conn_class for this test
        assert default_config['settings']['regular']['conn_class'] != 'K7'
        default_config['settings']['regular']['conn_class'] = 'K7'
    elif fixture_test_put_default_config_type == 'failure':
        default_config = { 'settings': 'garbage string' }
    else:
        raise NotImplementedError()

    # the default config.json should be updated
    config = backend.sim.get_default_config()
    assert default_config['settings'] != config['settings']
    ret = backend.sim.put_default_config(json.dumps(default_config))

    if fixture_test_put_default_config_type == 'success':
        config = backend.sim.get_default_config()
        assert default_config['settings'] == config['settings']

        assert ret['config']['version'] == 0
        assert ret['config']['settings'] == config['settings']
        assert ret['config']['execution'] == {
            "numCPUs": 1,
            "numRuns": 1
        }
        assert ret['config']['logging'] == 'all'
        assert ret['config']['log_directory_name'] == 'startTime'
        assert ret['config']['post'] == []
        assert ret['message'] == 'success'
    else:
        assert fixture_test_put_default_config_type == 'failure'
        assert ret['config'] is None
        assert ret['message'] != 'success'


def test_get_available_scheduling_functions():
    ret = backend.sim.get_available_scheduling_functions()
    assert 'SFNone' in ret
    assert 'MSF' in ret


def test_get_available_connectivities():
    ret = backend.sim.get_available_connectivities()
    assert 'Linear' in ret
    assert 'Random' in ret
    assert 'K7' in ret


def test_get_available_trace_files():
    trace_file_name = 'grenoble.k7.gz'
    trace_dir_path = backend.get_trace_dir_path()
    trace_file_path = os.path.join(trace_dir_path, trace_file_name)

    with gzip.GzipFile(trace_file_path, 'r') as f:
        config_line = f.readline()
        config = json.loads(config_line)

    assert len(os.listdir(trace_dir_path)) == 1
    assert os.path.exists(trace_file_path) is True

    ret = backend.sim.get_available_trace_files()
    assert len(ret) == 1
    assert ret[0]['file_name'] == trace_file_name
    assert ret[0]['file_path'] == os.path.abspath(trace_file_path)
    assert ret[0]['config'] == config


def test_start(default_settings):
    # set one (slotframe) to exec_numSlotframesPerRun so that the test
    # finishes in a short time
    default_settings['exec_numSlotframesPerRun'] = 1

    # _sim_engine should be None before starting a simulation
    assert backend.sim._sim_engine is None

    # call start()
    call_exposed_api(backend.sim.start, default_settings)

    # _sim_engine should be available now
    assert backend.sim._sim_engine is not None
    assert backend.sim._sim_engine.is_alive() is True

    # the simulator should yield the CPU at every end of slotframe
    assert (
        backend.sim._sim_engine.getAsn() ==
        (default_settings['tsch_slotframeLength'] - 1)
    )

    # sleep for a while. this makes the simulator run until it
    # finishes
    gevent.sleep(0.5)

    # the simulator should be finished
    assert backend.sim._sim_engine is None


def test_pause(sim_engine, default_settings):
    _sim_engine = sim_engine(default_settings)

    # the simulator should stop at the end of the first slotframe
    asn_before_sleep = _sim_engine.getAsn()

    # call pause()
    call_exposed_api(backend.sim.pause)

    # the simulator should stop at the next ASN of 'asn_before_sleep'
    assert _sim_engine.is_alive() is True
    assert _sim_engine.getAsn() == asn_before_sleep + 1


def test_resume(sim_engine, default_settings):
    _sim_engine = sim_engine(default_settings)

    # call pause()
    call_exposed_api(backend.sim.pause)

    # the simulator should stop at the next ASN of 'asn_before_sleep'
    asn_before_sleep = _sim_engine.getAsn()

    # sleep to yield the CPU
    gevent.sleep(0.001)

    # the simulator should still be paused
    assert _sim_engine.getAsn() == asn_before_sleep

    # call resume
    call_exposed_api(backend.sim.resume)

    # then, the simulator should proceed its global ASN by one slotframe
    assert _sim_engine.getAsn() == (
        asn_before_sleep + default_settings['tsch_slotframeLength'] - 1
    )


@pytest.fixture(params=['with_pause', 'without_pause'])
def pause_option(request):
    return request.param


def test_abort(sim_engine, default_settings, pause_option):
    _sim_engine = sim_engine(default_settings)

    # pause the simulation if necessary
    if pause_option == 'with_pause':
        # call pause()
        call_exposed_api(backend.sim.pause)
    else:
        assert pause_option == 'without_pause'

    # the simulator should be alive
    assert _sim_engine.is_alive() is True

    # call abort()
    call_exposed_api(backend.sim.abort)

    # sleep for a while
    gevent.sleep(0.5)

    # _sim_engine should be destroyed
    assert backend.sim._sim_engine is None


@pytest.fixture(params=['start', 'pause', 'resume', 'abort'])
def sim_action(request):
    return request.param


@pytest.fixture(params=[
    'success',
    'failure_on_sim_state',
    'failure_on_sim_existence']
)
def return_type(request):
    return request.param


def test_return_values(default_settings, sim_action, return_type):
    default_settings['exec_numSlotframesPerRun'] = 1

    if sim_action == 'start':
        if return_type == 'success':
            # use the default settings; do nothing
            pass
        elif return_type == 'failure_on_sim_existence':
            # set a dummy object to _sim_engine
            backend.sim._sim_engine = {}
        else:
            # make an error in settings
            del default_settings['exec_numMotes']

        ret_val = backend.sim.start(default_settings, stderr_redirect=False)

        if return_type == 'failure_on_sim_existence':
            # revert _sim_engine
            backend.sim._sim_engine = None
        else:
            assert backend.sim._sim_engine is None
    else:
        method_to_call = getattr(backend.sim, sim_action)
        greenlet = gevent.spawn(backend.sim.start, default_settings)
        if return_type == 'success':
            # start a simulation
            gevent.sleep(backend.sim.GEVENT_SLEEP_SECONDS_IN_SIM_ENGINE)
            if sim_action == 'resume':
                # make the simulation pause
                backend.sim.pause()
        else:
            # do nothing; _sim_engine is not available yet
            pass

        ret_val = method_to_call()
        if backend.sim._sim_engine is not None:
            backend.sim._destroy_sim()

        gevent.kill(greenlet)
        assert backend.sim._sim_engine is None

    if return_type == 'success':
        assert ret_val['status'] == backend.sim.RETURN_STATUS_SUCCESS
        assert 'message' not in ret_val
        assert 'trace' not in ret_val
    else:
        assert ret_val['status'] == backend.sim.RETURN_STATUS_FAILURE
        assert ret_val['message'] is not None


@pytest.fixture(params=['webapp', 'simulator'])
def target_git_repo(request):
    return request.param


@pytest.mark.skip
def test_get_git_info(target_git_repo):
    if target_git_repo == 'webapp':
        git_dir = os.path.join(backend.BACKEND_BASE_PATH, '..', '.git')
    else:
        with open(backend.BACKEND_CONFIG_PATH) as f:
            config = json.load(f)
            git_dir = os.path.join(
                os.path.dirname(backend.BACKEND_CONFIG_PATH),
                config['simulator_path'],
                '.git'
            )

    branch_name = subprocess.check_output([
        'git',
        '--git-dir',
        git_dir,
        'rev-parse',
        '--abbrev-ref',
        'HEAD'
    ]).strip()

    short_hash = subprocess.check_output([
        'git',
        '--git-dir',
        git_dir,
        'rev-parse',
        '--short=7',
        'HEAD'
    ]).strip()

    ret = backend.sim.get_git_info()
    assert ret[target_git_repo]['branch'] == branch_name
    assert ret[target_git_repo]['short_hash'] == short_hash
