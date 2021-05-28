#!/usr/bin/env python3
# real-time trip

class Time:
  def __init__(self, h, m):
    self.time = h*60+m
  def __str__(self):
    return f"{self.time//60:02d}:{self.time%60:02d}"
  def __add__(self, other):
    return Time(0, self.time + other.time)
  def __sub__(self, other):
    return Time(0, self.time - other.time)
  def __floordiv__(self, other):
    return self.time // other.time
  def __mul__(self, num):
    return Time(0, self.time * num)
  def __ge__(self, other):
    return self.time >= other.time

class Trip():
  # finite list of legs
  def __init__(self, legs):
    self.legs = legs
  def __getitem__(self, key):
    return self.legs[key]
  def __str__(self):
    return '\n'.join(["Trip:"] + [f"- {leg}" for leg in self.legs])
  def __radd__(self, seq):
    return Trip(seq + self.legs)
  def __len__(self):
    return len(self.legs)

class Leg:
  # atomic part of a trip
  # refineable
  def __init__(self, transport, loc_from, loc_to, departure, duration):
    self.transport = transport
    self.loc_from = loc_from
    self.loc_to = loc_to
    self.departure = departure
    self.duration = duration
  @property
  def arrival(self):
    return self.departure + self.duration if self.departure else None
  def __repr__(self):
    return f"Leg(\
{self.transport}, \
{self.loc_from}, \
{self.loc_to}, \
{self.departure}, \
{self.duration}, \
{self.arrival})"

class Transport:
  # a transport option
  # may be more polymorphic
  # refineable
  def __init__(self, kind, line, direction, mission):
    self.kind = kind
    self.line = line
    self.direction = direction  # A/R (or destination? no, this is mission)
    self.mission = mission
  def __repr__(self):
    return f"Transport(\
{self.kind}, \
{self.line}, \
{self.direction}, \
{self.mission})"

ident = 0
def p(r, s):
    pass
    #print(' ' * 3 * (3 - len(r)) + s)

T_METRO = "METRO "
T_RER   = "RER   "
T_WALK  = "Change"

def suggest_trips(request, departure):
  # trip constraints -> suggested trip iterator
  rest = request[1:]
  best = None
  for first in suggest_legs(request[0], departure):
    p(request, f'{first.departure} {len(rest)}')
    if best is not None and first.arrival >= best + margin:
      p(request, f"Cut: {len(request)} {first.arrival} first")
      break
    if not rest:
      p(request, "IF")
      yield Trip([first])
      continue
    p(request, f"else {len(rest)}")
    suggested_rests = suggest_trips(rest, departure=first.arrival)
    for suggested_rest in suggested_rests:
      trip = [first] + suggested_rest
      arrival = trip[-1].arrival
      if best is None:
        best = arrival
      elif arrival >= best + margin:
        p(request, f"Cut: {len(request)}  because {arrival} > = {best} + {margin} = {best + margin} ")
        break  # don't look further
      yield trip

def suggest_legs(request, departure):
  # leg constraints -> suggested leg iterator
  for schedule in find_schedules(request.transport, request.loc_from, departure):
    # TODO also estimate duration?
#    p(request, f"{departure} -> {schedule}")
    yield Leg(request.transport, request.loc_from, request.loc_to,
               schedule, request.duration)

SCHEDULES = {
  T_METRO: (Time(19, 5), Time(00,10), Time(23,30)),
  T_RER:   (Time(19,10), Time(00,30), Time(23,50)),
  T_WALK:  (Time(19,00), Time(00, 1), Time(23,50)),  # not meaningful
}

def find_schedules(transport, loc_from, departure):
  # constraints -> available departures iterator
  first, freq, last = SCHEDULES[transport.kind]
  for i in range((last-first)//freq):
    schedule = first + freq * i
#    p(request, f"{departure} -> {schedule} {schedule >= departure}")
    if schedule >= departure:
      # TODO also return refined transport (mission code)
      yield schedule
      if freq <= Time(0,1):
        print("Time 0.1 STOP")
        return
      else:
        print(f"NORMAL {freq}")

# test

M7 = Transport(T_METRO, '7', 'N', 'LCNV')
RA = Transport(T_RER, 'A', 'O', 'YVAN')
W = Transport(T_WALK, 'X', 'X', 'XXXX')

TRIP = Trip([
  Leg(M7, 'VLA', 'OPE', None, Time(00,25)),
  Leg(W,  'OPE', 'AUB', None, Time(00, 5)),
  Leg(RA, 'AUB', 'RMM', None, Time(00,20)),
])

margin = Time(0,31)

for i, suggested in enumerate(suggest_trips(TRIP, Time(19,30))):
  print(suggested)
  #if i >= 7: break

#
