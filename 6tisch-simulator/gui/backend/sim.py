from __future__ import division
from builtins import str
from builtins import map
from past.utils import old_div
import json
import gzip
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import types
import traceback

import eel
import gevent
import psutil

import backend
import backend.utils
from SimEngine import (
    SimEngine,
    SimSettings,
    SimLog
)


DUMMY_COMBINATION_KEYS = ['exec_numMotes']
SIM_LOG_FILTERS = 'all'
DEFAULT_LOG_NOTIFICATION_FILTER = [
    SimLog.LOG_SIMULATOR_STATE['type'],
    SimLog.LOG_SIMULATOR_RANDOM_SEED['type'],
    SimLog.LOG_MAC_ADD_ADDR['type']
]
GEVENT_SLEEP_SECONDS_IN_SIM_ENGINE = 0.001

RETURN_STATUS_SUCCESS = 'success'
RETURN_STATUS_FAILURE = 'failure'
RETURN_STATUS_ABORTED = 'aborted'

_sim_engine = None
_elapsed_minutes = 0


# exported functions


@eel.expose
def get_default_config():
    if os.path.exists(backend.SIM_CONFIG_PATH) is False:
        # someone has deleted our config.json file... recreate one
        backend.utils.create_config_json()

    with open(backend.SIM_CONFIG_PATH, 'r') as f:
        config = json.load(f)

    # convert a path of the trace file to the abosolute one
    original_config_path = os.path.join(backend.get_simulator_path(), 'bin')
    for settings_type in ['combination', 'regular']:
        if 'conn_trace' not in config['settings'][settings_type]:
            continue
        if isinstance(config['settings'][settings_type]['conn_trace'], list):
            config['settings'][settings_type]['conn_trace'] = list(map(
                lambda trace_file:
                os.path.abspath(os.path.join(original_config_path, trace_file))
                if os.path.isabs(trace_file) is False
                else trace_file
            ))
        elif (
                config['settings'][settings_type]['conn_trace']
                and
                (
                    os.path.isabs(
                        config['settings'][settings_type]['conn_trace']
                    ) is False
                )
            ):
            config['settings'][settings_type]['conn_trace'] = os.path.abspath(
                os.path.join(
                    original_config_path,
                    config['settings'][settings_type]['conn_trace']
                )
            )
        else:
            # it's an absolute path or None; it doesn't need the coversion
            pass

    return config


@eel.expose
def put_default_config(config_str):
    try:
        config = json.loads(config_str)
    except ValueError:
        return {
            'config': None,
            'message': 'No JSON object could be decoded'
        }

    new_config = backend.utils.CONFIG_JSON_TEMPLATE.copy()
    if 'settings' not in config:
        return {
            'config': None,
            'message': '"settings" is missing'
        }
    else:
        new_config['settings'] = config['settings']
        check_config_json = os.path.join(
        backend.get_simulator_path(),
        'bin/check_config_json.py'
    )

    # check the given config
    popen = subprocess.Popen(
        [sys.executable, check_config_json, '-s', '-c', '-'],
        stdin  = subprocess.PIPE,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )
    _, stderrdata = popen.communicate(json.dumps(new_config))

    if popen.returncode == 0:
        # if the check succeeds, update the default config.json
        new_config['settings'] = config['settings']
        # write the new config to the default config.json file
        with open(backend.SIM_CONFIG_PATH, 'w') as f:
            json.dump(new_config, f)
        ret = {
            'config': get_default_config(),
            'message': 'success'
        }
    else:
        # return error message
        ret = {
            'config': None,
            'message': stderrdata
        }

    return ret


@eel.expose
def get_available_scheduling_functions():
    sf_py_path = os.path.join(
        backend.get_simulator_path(),
        'SimEngine/Mote/sf.py'
    )
    ret_val = set()
    with open(sf_py_path, 'r') as f:
        ret_val = set(
            re.findall(r'SchedulingFunction\w+', f.read(), re.MULTILINE)
        )

    # remove "SchedulingFunctionBase" that is the base (super) class
    # for concrete scheduling function implementations
    ret_val.remove('SchedulingFunctionBase')

    # strip leading "SchedulingFunction" and return
    return [re.sub(r'SchedulingFunction(\w+)', r'\1', elem) for elem in ret_val]


@eel.expose
def get_available_trace_files():
    trace_dir_path = backend.get_trace_dir_path()
    ret = []
    for trace_dir_path, dirs, files in os.walk(trace_dir_path):
        for file_name in files:
            if re.match(r'.+\.k7\.gz$', file_name) is not None:
                trace_file_path = os.path.join(trace_dir_path, file_name)
                with gzip.GzipFile(trace_file_path, 'r') as f:
                    config_line = f.readline()
                    config = json.loads(config_line)
                ret.append({
                    'file_name': file_name,
                    'file_path': os.path.abspath(trace_file_path),
                    'config': config
                })
    return sorted(ret, key=lambda item: item['file_name'])


@eel.expose
def get_git_info():
    # to prevent memory leak, we will have a separate process to get
    # information of the Git repositories with gitpython:
    # https://gitpython.readthedocs.io/en/stable/intro.html#limitations
    get_git_info_cmd_path = os.path.join(
        backend.BACKEND_BASE_PATH,
        'get_git_info'
    )
    return json.loads(subprocess.check_output(
        [sys.executable, get_git_info_cmd_path])
    )


@eel.expose
def get_available_connectivities():
    conn_py_path = os.path.join(
        backend.get_simulator_path(),
        'SimEngine/Connectivity.py'
    )
    ret_val = set()
    with open(conn_py_path, 'r') as f:
        ret_val = set(
            re.findall(r'ConnectivityMatrix\w+', f.read(), re.MULTILINE)
        )

    # remove "ConnectivityMatrixBase" that is the base (super) class
    # for concrete scheduling function implementations
    ret_val.remove('ConnectivityMatrixBase')

    # strip leading "Connectivity" and return
    return [re.sub(r'ConnectivityMatrix(\w+)', r'\1', elem) for elem in ret_val]


@eel.expose
def start(settings, log_notification_filter='all', stderr_redirect=True):
    global _sim_engine
    global _elapsed_minutes

    sim_settings = None
    sim_log = None
    ret_val = {}

    if _sim_engine is not None:
        return {
            'status' : RETURN_STATUS_FAILURE,
            'message': 'SimEngine has been started already',
            'trace'  : None
        }

    try:
        sim_settings = SimSettings.SimSettings(
            cpuID        = 0,
            run_id       = 0,
            log_root_dir = backend.SIM_DATA_PATH,
            **settings
        )
        start_time = time.time()
        sim_settings.setLogDirectory(
            '{0}-{1:03d}'.format(
                time.strftime(
                    "%Y%m%d-%H%M%S",
                    time.localtime(start_time)
                ),
                int(round(start_time * 1000)) % 1000
            )
        )
        sim_settings.setCombinationKeys(DUMMY_COMBINATION_KEYS)

        sim_log = SimLog.SimLog()
        sim_log.set_log_filters(SIM_LOG_FILTERS)
        _overwrite_sim_log_log(log_notification_filter)

        _save_config_json(
            sim_settings,
            saving_settings = {
                'combination': {},
                'regular': settings.copy()
            }
        )

        crash_report_path = os.path.join(
            sim_settings.logRootDirectoryPath,
            sim_settings.logDirectory,
            'crash_report.log'
        )
        if stderr_redirect is True:
            _redirect_stderr(redirect_to=open(crash_report_path, 'w'))

        _sim_engine = SimEngine.SimEngine()
        _elapsed_minutes = 0
        _overwrite_sim_engine_actionEndSlotframe()

        # start and wait until the simulation ends
        _sim_engine.start()
        _sim_engine.join()
    except Exception as e:
        ret_val['status'] = RETURN_STATUS_FAILURE
        ret_val['message'] = str(e)
        ret_val['trace'] = traceback.format_exc()
    else:
        if _sim_engine.getAsn() == (
                sim_settings.exec_numSlotframesPerRun *
                sim_settings.tsch_slotframeLength
            ):
            ret_val['status'] = RETURN_STATUS_SUCCESS
            # rename .dat file and remove the subdir
            dat_file_path = sim_settings.getOutputFile()
            subdir_path = os.path.dirname(dat_file_path)
            new_file_name = subdir_path + '.dat'
            os.rename(dat_file_path, new_file_name)
            os.rmdir(subdir_path)
        else:
            # simulation is aborted
            ret_val['status'] = RETURN_STATUS_ABORTED
    finally:
        # housekeeping for crash_report and stderr
        if stderr_redirect is True:
            crash_report = _restore_stderr()
            crash_report.close()
            if os.stat(crash_report.name).st_size == 0:
                os.remove(crash_report.name)
            else:
                ret_val['crash_report_path'] = crash_report.name

        # cleanup
        if _sim_engine is None:
            if sim_settings is not None:
                sim_settings.destroy()
            if sim_log is not None:
                sim_log.destroy()
        else:
            _destroy_sim()

    return ret_val


@eel.expose
def pause():
    global _sim_engine

    try:
        # we cannot make the simulation pause on the current ASN because
        # of a limitation of the event scheduler; so we schedule pause on
        # the next ASN
        _sim_engine.pauseAtAsn(_sim_engine.getAsn() + 1)
    except Exception as e:
        return {
            'status':  RETURN_STATUS_FAILURE,
            'message': e,
            'trace': traceback.format_exc()
        }
    else:
        return {
            'status': RETURN_STATUS_SUCCESS
        }


@eel.expose
def resume():
    global _sim_engine

    try:
        _sim_engine.play()
    except Exception as e:
        return {
            'status':  RETURN_STATUS_FAILURE,
            'message': e,
            'trace': traceback.format_exc()
        }
    else:
        return {
            'status': RETURN_STATUS_SUCCESS
        }


@eel.expose
def abort():
    global _sim_engine
    try:
        _destroy_sim()
    except Exception as e:
        return {
            'status':  RETURN_STATUS_FAILURE,
            'message': e,
            'trace': traceback.format_exc()
        }
    else:
        return {
            'status': RETURN_STATUS_SUCCESS
        }


@eel.expose
def get_sim_data_path():
    return os.path.abspath(backend.SIM_DATA_PATH)


@eel.expose
def delete_all_results():
    for result_subdir_name in os.listdir(backend.SIM_DATA_PATH):
        delete_result(result_subdir_name)


@eel.expose
def delete_result(result_subdir_name):
    path = os.path.join(backend.SIM_DATA_PATH, result_subdir_name)
    shutil.rmtree(path)


@eel.expose
def get_total_number_of_results():
    return len(os.listdir(backend.SIM_DATA_PATH))


@eel.expose
def get_results(start_index, max_num_results):
    results = sorted(os.listdir(backend.SIM_DATA_PATH), reverse=True)
    end_index = start_index + max_num_results

    ret = []
    for result in results[start_index:end_index]:
        result_path = os.path.join(backend.SIM_DATA_PATH, result)
        last_modified = time.strftime(
            '%b %d %Y %H:%M:%S',
            time.localtime(os.path.getmtime(result_path))
        )
        try:
            with open(os.path.join(result_path, 'config.json')) as f:
                config = json.load(f)
                settings = config['settings']['regular']
                assert len(config['settings']['combination'])
                assert 'exec_numMotes' in config['settings']['combination']
                assert (
                    len(config['settings']['combination']['exec_numMotes']) == 1
                )
                settings['exec_numMotes'] = (
                    config['settings']['combination']['exec_numMotes'][0]
                )
        except (IOError, ValueError, TypeError):
            settings = None
        ret.append({
            'name': result,
            'last_modified': last_modified,
            'settings': settings
        })

    return ret


@eel.expose
def shutdown_backend():
    parent_backend_server_process = None
    parent_pid = os.getppid()
    for proc in psutil.process_iter(attrs=['pid', 'cmdline']):
        if proc.info['cmdline'] is None:
            continue
        elif 'backend/start' in proc.info['cmdline']:
            if proc.info['pid'] == parent_pid:
                parent_backend_server_process = proc

    if parent_backend_server_process is None:
        # this backend process was invoked directly
        os.kill(os.getpid(), signal.SIGINT)
    else:
        # this backend process was invoked by the parent process of
        # 'backend/start --auto-restart'; kill our parent process
        os.kill(parent_pid, signal.SIGINT)


def _overwrite_sim_engine_actionEndSlotframe():
    global _sim_engine

    _sim_engine.original_actionEndSlotframe = _sim_engine._actionEndSlotframe

    def _new_actionEndSlotframe(self):
        global _elapsed_minutes

        self.original_actionEndSlotframe()
        asn = _sim_engine.getAsn()
        minutes = math.floor(old_div(asn * _sim_engine.settings.tsch_slotDuration, 60))
        if _elapsed_minutes < minutes:
           _elapsed_minutes = minutes
           eel.notifyLogEvent({
               '_type': '_backend.tick.minute',
               '_asn': asn,
               'currentValue': _elapsed_minutes
           })
        # we need to yield the CPU explicitly for other tasks because
        # threading is monkey-patched by gevent. see __init__.py.
        gevent.sleep(GEVENT_SLEEP_SECONDS_IN_SIM_ENGINE)

    _sim_engine._actionEndSlotframe = types.MethodType(
        _new_actionEndSlotframe,
        _sim_engine
    )


def _overwrite_sim_log_log(log_notification_filter):
    if log_notification_filter == 'all':
        _filter = 'all'
    elif isinstance(log_notification_filter, str):
        _filter = DEFAULT_LOG_NOTIFICATION_FILTER
        _filter.append(log_notification_filter)
    elif isinstance(log_notification_filter, list):
        _filter = DEFAULT_LOG_NOTIFICATION_FILTER + log_notification_filter
    else:
        raise RuntimeError('unsupported type for log_notification_filter')

    sim_log = SimLog.SimLog()
    sim_log.original_log = sim_log.log

    def _new_log(self, simlog, content):
        self.original_log(simlog, content)

        # content is expected to be updated adding _asn, _type
        assert '_asn' in content
        assert '_type' in content

        if (
                (_filter == 'all')
                or
                (content['_type'] in _filter)
            ):
            eel.notifyLogEvent(content)
        else:
            pass

    sim_log.log = types.MethodType(_new_log, sim_log)


def _save_config_json(sim_settings, saving_settings):
    # put config.json under the data directory
    saving_settings['combination']['exec_numMotes'] = [
        saving_settings['regular']['exec_numMotes']
    ]
    del saving_settings['regular']['exec_numMotes']

    saving_config = get_default_config()
    saving_config['settings'] = saving_settings
    saving_config_path = os.path.join(
        sim_settings.logRootDirectoryPath,
        sim_settings.logDirectory,
        'config.json'
    )
    with open(saving_config_path, 'w') as f:
        json.dump(saving_config, f, indent=4)


def _redirect_stderr(redirect_to):
    sys.stderr = redirect_to


def _restore_stderr():
    redirect_to = sys.stderr
    sys.stderr = sys.__stderr__
    return redirect_to


def _destroy_sim():
    global _sim_engine
    global _elapsed_minutes

    sim_log = SimLog.SimLog()
    connectivity = _sim_engine.connectivity
    sim_settings = _sim_engine.settings

    _sim_engine.destroy()
    sim_log.destroy()
    connectivity.destroy()
    sim_settings.destroy()

    _sim_engine = None
    _elapsed_minutes = 0


def clear_sim():
    global _sim_engine
    if _sim_engine == None:
        # nothing to do
        pass
    else:
        _destroy_sim()
