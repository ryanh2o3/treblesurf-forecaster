
import os
#import arrow
#import requests
import math

def retrieve5DayWeather(latitude, longitude):
  start = arrow.now()
  end = arrow.now().shift(hours=+1)

  response = requests.get(
    'https://api.stormglass.io/v2/weather/point',
    params={
      'lat': latitude,
      'lng': longitude,
      'params': ','.join([ 'swellHeight']),
      'start': start.to('UTC').timestamp(),  # Convert to UTC timestamp
      'end': end.to('UTC').timestamp()  # Convert to UTC timestamp
    },
    headers={
      'Authorization': '40b76f9e-28e6-11ee-8d52-0242ac130002-40b7702a-28e6-11ee-8d52-0242ac130002'
    }
  )
  json_data = response.json()
  return response.json()


#data = retrieve5DayWeather(55.266605, -8.088004)
#print(data)

# Ballymastocker
# {'hours': [{'swellHeight': {'dwd': 0.51, 'noaa': 0.27, 'sg': 0.51}, 'time': '2024-06-13T20:00:00+00:00'}, {'swellHeight': {'dwd': 0.5, 'noaa': 0.06, 'sg': 0.5}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:37', 'lat': 55.186844, 'lng': -7.59785, 'params': ['swellHeight'], 'requestCount': 19, 'start': '2024-06-13 20:00'}}
# Ballyhiernan
# {'hours': [{'swellHeight': {'dwd': 0.76, 'meteo': 1.21, 'noaa': 0.32, 'sg': 1.21}, 'time': '2024-06-13T20:00:00+00:00'}, {'swellHeight': {'dwd': 0.71, 'meteo': 1.16, 'noaa': 0.08, 'sg': 1.16}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:38', 'lat': 55.250232, 'lng': -7.701494, 'params': ['swellHeight'], 'requestCount': 20, 'start': '2024-06-13 20:00'}}
# Out at sea swell
# {'hours': [{'swellHeight': {'dwd': 0.89, 'meteo': 1.21, 'noaa': 0.1, 'sg': 1.21}, 'time': '2024-06-13T20:00:00+00:00'}, {'swellHeight': {'dwd': 0.82, 'meteo': 1.16, 'noaa': 0.09, 'sg': 1.16}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:40', 'lat': 55.30636, 'lng': -7.876486, 'params': ['swellHeight'], 'requestCount': 21, 'start': '2024-06-13 20:00'}}
# Out at sea further out
# {'hours': [{'swellHeight': {'dwd': 0.89, 'meteo': 1.21, 'noaa': 0.1, 'sg': 1.21}, 'time': '2024-06-13T20:00:00+00:00'}, {'swellHeight': {'dwd': 0.82, 'meteo': 1.16, 'noaa': 0.09, 'sg': 1.16}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:48', 'lat': 55.266605, 'lng': -8.088004, 'params': ['swellHeight'], 'requestCount': 25, 'start': '2024-06-13 20:00'}}
# Out at sea wave height
# {'hours': [{'time': '2024-06-13T20:00:00+00:00', 'waveHeight': {'dwd': 0.94, 'meteo': 1.62, 'noaa': 0.9, 'sg': 1.62}}, {'time': '2024-06-13T21:00:00+00:00', 'waveHeight': {'dwd': 0.95, 'meteo': 1.6, 'noaa': 0.93, 'sg': 1.6}}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:42', 'lat': 55.30636, 'lng': -7.876486, 'params': ['waveHeight'], 'requestCount': 22, 'start': '2024-06-13 20:00'}}
# Out at sea secondary swell height
# {'hours': [{'secondarySwellHeight': {'noaa': 0.27, 'sg': 0.27}, 'time': '2024-06-13T20:00:00+00:00'}, {'secondarySwellHeight': {'noaa': 0.14, 'sg': 0.14}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:44', 'lat': 55.30636, 'lng': -7.876486, 'params': ['secondarySwellHeight'], 'requestCount': 23, 'start': '2024-06-13 20:00'}}
# Out at sea secondary further
# {'hours': [{'secondarySwellHeight': {'noaa': 0.27, 'sg': 0.27}, 'time': '2024-06-13T20:00:00+00:00'}, {'secondarySwellHeight': {'noaa': 0.14, 'sg': 0.14}, 'time': '2024-06-13T21:00:00+00:00'}], 'meta': {'cost': 1, 'dailyQuota': 500, 'end': '2024-06-13 21:47', 'lat': 55.266605, 'lng': -8.088004, 'params': ['secondarySwellHeight'], 'requestCount': 24, 'start': '2024-06-13 20:00'}}

import pygrib
import numpy as np

# Open the grib file
grbs = pygrib.open('test.grib2')

# Select the first message
grb = grbs.select(name='Mean period of wind waves')[0]

print(grb.values)
# Close the grib file
grbs.close()

