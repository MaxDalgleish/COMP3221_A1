python3 COMP3221_A1_Routing.py A 6000 Config_Files/Aconfig.txt &
PIDA=$!
echo $PIDA

sleep 5
kill -INT $PIDA
echo "Process killed"