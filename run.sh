#!/bin/bash

python3 COMP3221_A1_Routing.py A 6000 Config_Files/Aconfig.txt &
PIDA=$!
python3 COMP3221_A1_Routing.py B 6001 Config_Files/Bconfig.txt &
PIDB=$!
python3 COMP3221_A1_Routing.py C 6002 Config_Files/Cconfig.txt &
PIDC=$!
python3 COMP3221_A1_Routing.py D 6003 Config_Files/Dconfig.txt &
PIDD=$!
python3 COMP3221_A1_Routing.py E 6004 Config_Files/Econfig.txt &
PIDE=$!
python3 COMP3221_A1_Routing.py F 6005 Config_Files/Fconfig.txt &
PIDF=$!
python3 COMP3221_A1_Routing.py G 6006 Config_Files/Gconfig.txt &
PIDG=$!
python3 COMP3221_A1_Routing.py H 6007 Config_Files/Hconfig.txt &
PIDH=$!
python3 COMP3221_A1_Routing.py I 6008 Config_Files/Iconfig.txt &
PIDI=$!
python3 COMP3221_A1_Routing.py J 6009 Config_Files/Jconfig.txt &
PIDJ=$!

sleep 30

kill -2 $PIDA
kill -2 $PIDB
kill -2 $PIDC
kill -2 $PIDD
kill -2 $PIDE
kill -2 $PIDF
kill -2 $PIDG
kill -2 $PIDH
kill -2 $PIDI
kill -2 $PIDJ

echo "All processes killed"