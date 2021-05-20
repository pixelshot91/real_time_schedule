#!/usr/bin/env python3

import urllib.request
import urllib.parse
import json
from datetime import datetime, date, time, timedelta
import re
from colorama import Fore, Back, Style
from sty import fg, bg, ef, rs
from collections import namedtuple
import yaml

import unittest

# Color
# Should use https://data.ratp.fr/explore/dataset/pictogrammes-des-lignes-de-metro-rer-tramway-bus-et-noctilien/information/
# but it only provide svg pictogram, not the background color
# https://fr.wikipedia.org/w/index.php?title=Mod%C3%A8le:Bus_RATP/couleur_fond&action=edit

def wrap_style(style, text):
    return style + text + bg.rs + ef.rs

# TODO: add direction to transport
class Transport(namedtuple('Transport', ['kind', 'line'])):
    SYMBOLS = {
        ('buses', '172'): wrap_style(bg(0, 100, 60), '172'),
        ('rers', 'B'):  wrap_style(bg(60, 145, 220), 'RER B'),
        }
    def __str__(self):
        return self.SYMBOLS[self]

class LocTime:
    def __init__(self, location, time):
        self.location = location
        self.time = time
    def __str__(self):
        if self.time is None:
            return 'XX:XX' + ' ' + self.location
        return self.time.strftime("%H:%M") + ' ' + self.location
    def __repr__(self):
        return repr(self.time)

class Leg(namedtuple('Leg', ['transport', 'xfrom', 'to', 'direction', 'duration'])):
    def __str__(self):
        return f'''{self.transport}
* {self.xfrom}
|
* {self.to}'''
    def __repr__(self):
        return f'Leg({self.transport!r}, from={self.xfrom!r}, to={self.to!r})'

# Convert an absolute time to datetime of today
def dt_abs(time):
    return datetime.combine(date.today(), time)

def call_api(*args):
    url = f'https://api-ratp.pierre-grimaud.fr/v4/' + '/'.join(args)
    print(url)
    f = urllib.request.urlopen(url)
    raw_response = f.read().decode('utf-8')
    return json.loads(raw_response)

def stations_slug_get(transport, slug):
    # TODO implement
    return slug

def make_leg(req, time):
    new_from = LocTime(req.xfrom.location, time)
    new_to = LocTime(req.to.location, time + timedelta(minutes=req.duration))
    return Leg(req.transport, new_from, new_to, req.direction, req.duration)

# TODO: the direction should be derived from the destination station
# TODO: cache results
def get_schedules(req):
    r = call_api(
        'schedules',
        req.transport.kind,
        req.transport.line,
        stations_slug_get(req.transport, req.xfrom.location),
        req.direction)
    to_times = {
            'buses': bus_schedule_absolute_time,
            'rers': rer_schedule_absolute_time,
    }
    times = to_times[req.transport.kind](r)
    return [ make_leg(req, t) for t in times ]

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

def find_next_schedule(suggested_legs, time):
    for l in suggested_legs:
        if l.xfrom.time > time:
            return l

def compute_itinerary(legs):
    first_leg = legs[0]
    possible_first_legs = get_schedules(first_leg)
    itineraries = []
    for pl in possible_first_legs:
        t = pl.to.time
        it = [pl]
        for requested_leg in legs[1:]:
            suggested_leg = find_next_schedule(get_schedules(requested_leg), t)
            if suggested_leg is None:
                break
            it.append(suggested_leg)
            t = suggested_leg.to.time
        else:
            itineraries.append(it)
    return itineraries

def pretty_print(itineraries):
    if not itineraries:
        print('No iteneraries found')
    for it in itineraries:
        for leg in it:
            print(leg)
        print()

if __name__ == '__main__':
    with open('trip.yaml', 'r') as trip_file:
        trip = yaml.load(trip_file, Loader=yaml.Loader)
        legs = [Leg(
            Transport(l['kind'], l['line']),
            LocTime(l['station_from'], None),
            LocTime(l['station_to'], None),
            l['direction'],
            l['duration'],
        ) for l in trip]
    pretty_print(compute_itinerary(legs))

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
