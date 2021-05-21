# Real-time public transport schedules

Many apps provide real-time schedule for public transport stations (RATP, ViaNavigo, SNCF).
Many apps provide provide itineraries from one place to another using public
transport (RATP, ViaNavigo, SNCF, Google Maps).
However theses itineraries are based on theoretical schedule, not on the
real-time one (Only Citymapper seems to get it right).
When the public transport (abreviated PT) is on schedule, it is not a problem, but delay happen
frequently.

This app only use real-time schedule from the RAPT API to suggest itinerary.
So the chance of your trip being disturbed is greatly reduced (however not cancelled).

## Source of Information
The official RATP API is available here.
https://data.ratp.fr/explore/dataset/horaires-temps-reel/information/
It provide real-time schedule for all RATP buses and the RATP part of the
RER A and B.
The API is free and the request cap is 30 000 000 request per month.
However, one has to fill a form to register his IP address to use it.
So this app does not use this API directly, but a proxy:
https://github.com/pgrimaud/horaires-ratp-api
Which make information available to all, and in JSON, instead of SOAP.

## Problems
### Limited look-ahead problem
The RATP only provide the next few passage of a PT. For buses, it only provide
the schedule of the next 2 buses. To get the schedule further in the future, we
can look for schedule in the previous stations and estimate ourself the time it
will take the PT to reach the stop of interest.

### RATP provide misleading information
For some PT line, (e.g. the T7), the RAPT does not provide the exact schedule of
a tram if it is too remote. Example: if the next tram is in 7 minutes, the next
in 40 minutes; the station display will read:
```
Athis-Mons 7
The next one +30
```

As the RATP API seems to provide an exact copy of the station display, the API
will read ["7 mn", "30 min"]. But the "30 mn" value is false and there is no
(obvious) way to know it.
One work around would be to consider all "30 mn" value to be false and ignore
them.

## TODO
To access SNCF information (part of RER A and B, RER C, D and E), we shoud use this
API:
https://ressources.data.sncf.com/explore/dataset/api-temps-reel-transilien/information/
