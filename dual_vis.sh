#!/bin/sh
python dual_vis_messenger_server.py &
6tisch-simulator/gui/backend/start &
open http://127.0.0.1:8080/
cd swarmsimmaster
python swarmsim.py
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT