import os
import requests
import arrow
import json
from datetime import datetime
from .dynamodb_service import *

API_URL = "https://api.stormglass.io/v2/weather/point"
API_KEY = os.environ.get('STORMGLASS_API_KEY')

def retrieve_forecast(latitude, longitude):
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
    
    if response.status_code != 200:
        raise Exception(f"Error fetching data from StormGlass API: {response.status_code} {response.text}")
    
    forecast_data = response.json()
    formatted_data = format_forecast_data(forecast_data)
    
    return formatted_data

def format_forecast_data(forecast_data):
    formatted_forecast = []
    forecast_date = datetime.utcnow().strftime('%Y-%m-%d')
    
    for hour in forecast_data['hours']:
        entry = {
            'forecastDate': forecast_date,
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
        }
        formatted_forecast.append(entry)
    
    return formatted_forecast