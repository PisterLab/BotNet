#!/bin/bash
cd swarmsimmaster/
python rpyc_server.py &
python ../6tisch-simulator/bin/runSim.py
