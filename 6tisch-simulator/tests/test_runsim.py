import os
import subprocess

#============================ helpers =========================================

#============================ tests ===========================================

def test_runSim():
    wd = os.getcwd()
    os.chdir("bin/")
    rc = subprocess.call(
        "python runSim.py",
        shell=True,
    )
    os.chdir(wd)
    assert rc==0
