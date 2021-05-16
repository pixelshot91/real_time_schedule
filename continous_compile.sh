#!/bin/bash
#when-changed -v -1 main.py -c "python3 main.py"
#when-changed -v -1 -s main.py -c "clear && python3 main.py"
when-changed -v -1 -s main.py -c "clear && date && python3 -m unittest main.py"
