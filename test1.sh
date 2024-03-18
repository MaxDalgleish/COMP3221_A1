#!/bin/bash

python3 COMP3221_A1_Routing.py A 6000 Config_Files/Xconfig.txt &
PIDA=$!
python3 COMP3221_A1_Routing.py D 6003 Config_Files/Yconfig.txt &
PIDD=$!
python3 COMP3221_A1_Routing.py G 6006 Config_Files/Zconfig.txt &
PIDG=$!

sleep 30

kill -2 $PIDA
kill -2 $PIDD
kill -2 $PIDG

echo "All processes killed"