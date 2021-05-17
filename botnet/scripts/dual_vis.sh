#!/bin/sh
python ./botnet/scripts/BotNetVisualizer.py &
6tisch-simulator/gui/backend/start &
sleep 3
open http://127.0.0.1:8080/
cd swarmsimmaster
python swarmsim.py
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT