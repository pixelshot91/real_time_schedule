#!/bin/bash
#when-changed -v -1 main.py -c "python3 main.py"
#when-changed -v -1 -s main.py -c "clear -x && date && python3 main.py"
#when-changed -v -1 -s main.py -c "clear -x && date && python3 -m unittest main.py"

when-changed -v -1 -s main.py trip.yaml -c "clear -x && date && python3 -m unittest main.py && python3 main.py"
