#!/usr/bin/env python3

import urllib.request
import urllib.parse
import json
from datetime import datetime, date, time, timedelta
import re

import unittest

# Convert an absolute time to datetime of today
def dt_abs(time):
    return datetime.combine(date.today(), time)

def call_api(*args):
    url = f'https://api-ratp.pierre-grimaud.fr/v4/' + '/'.join(args)
    print(url)
    f = urllib.request.urlopen(url)
    raw_response = f.read().decode('utf-8')
    return json.loads(raw_response)

def get_bus_schedules_json():
    return call_api('schedules', 'buses', '172', 'villejuif%2B%2B%2Blouis%2Baragon', 'R')
#print(get_bus_schedules_json())

def get_rer_schedules_json():
    return call_api('schedules', 'rers', 'b', 'bourg%2Bla%2Breine', 'R')
#print(get_rer_schedules_json())

def get_rer_missions_json(code):
    return call_api('missions', 'rers', 'B', code)
#print(get_rer_missions_json('SECO'))

# Returns wether the RER with mission code "m" go to Massy-Verrières
# Ex: * KASE -> True
#     * PISE -> False
def go_to_MV(m):
    with open('missions_code.txt', 'r') as missions_file:
        missions = json.load(missions_file)
    if m not in missions:
        try:
            resp = get_rer_missions_json(m)
            missions[m] = [ s['name'] for s in resp['result']['stations'] ]
        except urllib.error.HTTPError as e:
            # "Sans voyageurs" mission return status 400
            if e.code == 400:
                missions[m] = []
            else:
                print(f'Error: {e}')
                return False
        print(f'Updating file with code {m}')
        with open('missions_code.txt', 'w') as missions_file:
            json.dump(missions, missions_file)
    return "Massy Verrieres" in missions[m]

def filter_MV(resp):
    resp['result']['schedules'] = list(filter(lambda s: go_to_MV(s['code']), resp['result']['schedules']))
    return resp

# Convert RATP human string to timedelta object
# Ex:
# * convert "3 mn" to timedelta(minutes=3)
# * convert "A l'approche" to timedelta(minutes=3)
# * convert "A l'arret" to timedelta(0)
def parse_bus_schedule_msg(msg):
    if msg == "A l'arret":
        return timedelta()
    if msg == "A l'approche":
        return timedelta(minutes=1)
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
        return dt_abs(time(int(res.group(1)),int(res.group(2))))
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

def find_next_schedule(schedules, time):
    for s in schedules:
        if s > time:
            return s

def compute_itinerary():
    buses_schedules = bus_schedule_absolute_time(get_bus_schedules_json())
    rer_schedules = rer_schedule_absolute_time(filter_MV(get_rer_schedules_json()))

    itineraries = []
    for bs in buses_schedules:
        it = [('VJ departure', bs)]

        # TODO: Use real-time schedule from previous station
        estimated_bus_travel_duration = timedelta(minutes=20)
        blr_arrival_time = bs + estimated_bus_travel_duration
        it.append(('BlR bus arrival', blr_arrival_time))

        blr_departure_time = find_next_schedule(rer_schedules, blr_arrival_time)
        if blr_departure_time is None:
            continue
        it.append(('BlR RER departure', blr_departure_time))

        itineraries.append(it)
    return itineraries

def pretty_print(itineraries):
    if not itineraries:
        print('No iteneraries found')
    for it in itineraries:
        for (label, dt) in it:
            print(f'{label} {dt.strftime("%H:%M")}')
        print()

if __name__ == '__main__':
    pretty_print(compute_itinerary())

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
        expected = [now, now + timedelta(minutes=1), dt_abs(time(17,47))]
        self.assertAlmostEqualTime(rer_schedule_absolute_time(resp), expected)
