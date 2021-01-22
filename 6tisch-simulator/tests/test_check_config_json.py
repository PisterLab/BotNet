import json
import os
import subprocess

import pytest


@pytest.fixture(params=[
    'success',
    'not found',
    'not json',
    'missing setting',
    'unsupported setting'
])
def fixture_test_type(request):
    return request.param


def test_check_config_json(fixture_test_type):
    root_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..'
        )
    )
    config_json = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        '..',
        'bin/config.json'
    )
    with open(config_json, 'r') as f:
        config = json.load(f)
        config = config
        assert 'settings' in config
        assert 'regular' in config['settings']
        assert 'sf_class' in config['settings']['regular']
    check_config_json = os.path.join(
        root_path,
        'bin/check_config_json.py'
    )
    resulting_exception = None
    popen = None

    try:
        if fixture_test_type == 'success':
            subprocess.check_output(
                [check_config_json, '-c', config_json]
            )
        elif fixture_test_type == 'not found':
            config_json = os.path.join(
                os.path.dirname(__file__),
                'non_existent_dir',
                'config.json'
            )
            expected_error_message = 'config.json is not found'
            popen = subprocess.Popen(
                [check_config_json, '-c', config_json],
                stderr = subprocess.PIPE
            )
            stdoutdata, stderrdata = popen.communicate()
            assert 'config.json is not found' in stderrdata.decode('utf-8')
        elif fixture_test_type == 'not json':
            wrong_config = u'garbage text' + json.dumps(config)
            popen = subprocess.Popen(
                [check_config_json, '-c', '-'],
                stdin = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            stdoutdata, stderrdata = popen.communicate(wrong_config.encode('utf-8'))
            assert 'No JSON object could be decoded' in stderrdata.decode('utf-8')
        elif fixture_test_type == 'missing setting':
            # remove sf_class from config
            config['settings']['regular'].pop('sf_class')
            popen = subprocess.Popen(
                [check_config_json, '-c', '-'],
                stdin = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            stdoutdata, stderrdata = popen.communicate(json.dumps(config).encode('utf-8'))
            assert '"sf_class" is missing' in stderrdata.decode('utf-8')
        elif fixture_test_type == 'unsupported setting':
            config['settings']['regular']['dummy_setting'] = 'garbage'
            popen = subprocess.Popen(
                [check_config_json, '-c', '-'],
                stdin = subprocess.PIPE,
                stderr = subprocess.PIPE
            )
            stdoutdata, stderrdata = popen.communicate(json.dumps(config).encode('utf-8'))
            assert '"dummy_setting" is not supported' in stderrdata.decode('utf-8')

    except subprocess.CalledProcessError as e:
        resulting_exception = e

    if fixture_test_type == 'success':
        assert resulting_exception is None
    else:
        if resulting_exception is not None:
            assert resulting_exception.returncode == 1
            assert resulting_exception
        elif popen is not None:
            assert popen.returncode == 1
        else:
            assert False
