#!/usr/bin/env python3

import urllib.request
import urllib.parse
import json
from datetime import datetime, date, time, timedelta
import re

import unittest

def get_schedules_json(type, code, station, way):
    url = f'https://api-ratp.pierre-grimaud.fr/v4/schedules/{type}/{code}/{station}/{way}'
    f = urllib.request.urlopen(url)
    raw_response = f.read().decode('utf-8')
    return json.loads(raw_response)

def get_bus_schedules_json():
    return get_schedules_json('buses', '172', 'villejuif%2B%2B%2Blouis%2Baragon', 'R')
#print(get_bus_schedules_json())

def get_rer_schedules_json():
    return get_schedules_json('rers', 'b', 'bourg%2Bla%2Breine', 'R')
#print(get_rer_schedules_json())

# Convert RATP human string to timedelta object
# Ex:
# * convert "3 mn" to timedelta(minutes=3)
# * convert "A l'arret" to timedelta(0)
def parse_bus_schedule_msg(msg):
    if msg == "A l'arret":
        return timedelta()
    if res := re.fullmatch(r'(\d+) mn', msg):
        return timedelta(minutes=int(res.group(1)))
    return None
# Ex:
# * convert "17:32 Voie 1" to time(hour=17, minutes=32)
# * convert "A l'approche Voie 2B" to now + time(minutes=1)
# * convert "Train à quai V.2" to now
def parse_rer_schedule_msg(msg):
    if msg.startswith("Train à quai"):
        return datetime.now()
    if msg.startswith("A l'approche"):
        return datetime.now() + timedelta(minutes=1)
    if res := re.match(r'(\d+):(\d+)', msg):
        return date.today() + timedelta(hours=int(res.group(1)), minutes=int(res.group(2)))
    return None

def bus_schedule_absolute_time(resp):
    schedules_json = resp['result']['schedules']
    schedules_duration = [ d  for s in schedules_json if (d := parse_bus_schedule_msg(s['message'])) is not None]
    now = datetime.now()
    schedules = [ now + delta for delta in schedules_duration ]
    return schedules

def rer_schedule_absolute_time(resp):
    schedules_json = resp['result']['schedules']
    schedules = [ d  for s in schedules_json if (d := parse_rer_schedule_msg(s['message'])) is not None]
    return schedules

class TestRATP(unittest.TestCase):
    def assertAlmostEqualTime(self, first, second, delta=timedelta(seconds=1)):
        self.assertEqual(len(first), len(second))
        for (f,s) in zip(first, second):
            self.assertAlmostEqual(f, s, delta=delta)
    def test_parse_bus_schedule_msg(self):
        self.assertEqual(parse_bus_schedule_msg("A l'arret"), timedelta())
        self.assertEqual(parse_bus_schedule_msg('3 mn'), timedelta(minutes=3))
    def test_bus_schedule_absolute_time(self):
        resp = {'result': {'schedules': [{'message': '8 mn', 'destination': 'Bourg-La-Reine RER'}, {'message': '26 mn', 'destination': 'Bourg-La-Reine RER'}, {'message': 'PAS DE SERVICE', 'destination': 'Bourg la Reine RER'}, {'message': '..................', 'destination': 'Bourg la Reine RER'}]}, '_metadata': {'call': 'GET /schedules/buses/172/villejuif%2B%2B%2Blouis%2Baragon/R', 'date': '2021-05-16T16:48:08+02:00', 'version': 4}}
        now = datetime.now()
        expected = [now + timedelta(minutes=8), now + timedelta(minutes=26)]
        self.assertAlmostEqualTime(bus_schedule_absolute_time(resp), expected)
    def test_rer_schedule_absolute_time(self):
        resp = {
          "result": {
            "schedules": [
              {
                "code": "EPOU",
                "message": "Train à quai V.2",
                "destination": "Aeroport Charles de Gaulle 2 TGV"
              },
              {
                "code": "GSZZ",
                "message": "A l'approche Voie 2B",
                "destination": "Aulnay-sous-Bois"
              },
              {
                "code": "ERBE",
                "message": "17:47 Voie 2",
                "destination": "Aeroport Charles de Gaulle 2 TGV"
              }
            ]
          },
          "_metadata": {
            "call": "GET /schedules/rers/b/bourg%2Bla%2Breine/A%2BR",
            "date": "2021-05-16T17:41:03+02:00",
            "version": 4
          }
        }
        now = datetime.now()
        expected = [now, now + timedelta(minutes=1), date.today() + timedelta(hours=17,minutes=47)]
        self.assertAlmostEqualTime(rer_schedule_absolute_time(resp), expected)
