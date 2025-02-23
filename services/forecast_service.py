import os
import requests
import arrow
import json
from datetime import datetime
from .dynamodb_service import *
from utils.calculations import *

API_URL = "https://api.stormglass.io/v2/weather/point"
API_KEY = os.environ.get('STORMGLASS_API_KEY')

def retrieve_forecast(latitude, longitude, beach_direction, ideal_swell_direction, country, region, spot):
    start = arrow.now()
    end = arrow.now().shift(days=+10).ceil('day')
    
    params = {
        'lat': latitude,
        'lng': longitude,
        'params': 'airTemperature,humidity,pressure,windSpeed,precipitation,windDirection,waterTemperature,swellHeight,swellPeriod,swellDirection',
        'start': start,
        'end': end
    }
    
    headers = {
        'Authorization': API_KEY
    }
    
    response = requests.get(API_URL, params=params, headers=headers)
    print(response)
    
    if response.status_code != 200:
        raise Exception(f"Error fetching data from StormGlass API: {response.status_code} {response.text}")
    
    forecast_data = response.json()
    formatted_data = format_forecast_data(forecast_data, beach_direction, ideal_swell_direction)
    for data in formatted_data:
            forecast_date = data['forecastDate']
            sort_key = f"{country}_{region}_{spot}"
            save_forecast_data(data, forecast_date, sort_key)
    return

def format_forecast_data(forecast_data, beach_direction, ideal_swell_direction):
    formatted_forecast = []
    
    for hour in forecast_data['hours']:
        entry = {
            'forecastDate': arrow.now().format('YYYY-MM-DD HH:mm:ss'),
            'dateForecastedFor': arrow.get(hour['time']).format('YYYY-MM-DD HH:mm:ss'),
            'temperature': hour.get('airTemperature', {}).get('sg'),
            'humidity': hour.get('humidity', {}).get('sg'),
            'pressure': hour.get('pressure', {}).get('sg'),
            'windSpeed': hour.get('windSpeed', {}).get('sg'),
            'precipitation': hour.get('precipitation', {}).get('sg'),
            'windDirection': hour.get('windDirection', {}).get('sg'),
            'waterTemperature': hour.get('waterTemperature', {}).get('sg'),
            'swellHeight': hour.get('swellHeight', {}).get('noaa'),
            'swellPeriod': hour.get('swellPeriod', {}).get('noaa'),
            'swellDirection': hour.get('swellDirection', {}).get('noaa'),
            # 'surfSize': calculate_surf_size(
            #     swell_height=hour.get('swellHeight', {}).get('noaa'),
            #     swell_period=hour.get('swellPeriod', {}).get('noaa'),
            #     beach_direction=beach_direction,
            #     swell_direction=hour.get('swellDirection', {}).get('noaa')
            # ),
            # 'waveEnergy': calculate_wave_energy(hour['swellHeight'], hour['swellPeriod']),
            # 'relativeWindDirection': calculateRelativeWindDirection(hour['windDirection'], beach_direction),
            # 'surfMessiness': calculateSurfMessiness(hour['windSpeed'], hour['windDirection'], beach_direction),
            # 'directionQuality': calculateDirectionQuality(hour['swellDirection'], ideal_swell_direction),
        }
        formatted_forecast.append(entry)
        print(formatted_forecast)
    
    return formatted_forecast