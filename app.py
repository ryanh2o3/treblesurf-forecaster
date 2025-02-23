
import json
import os
import boto3
from services.forecast_service import *
from services.dynamodb_service import *

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    try:
        # Get location data first
        locations = get_location_data()
        # Get forecast for each location
        forecastDate = arrow.now().format('YYYY-MM-DD HH')
        loops = 0
        for location in locations:
            if loops == 1:
                break
            loops += 1
            print(forecastDate)
            print(location)
            parsed_location = parse_location_data(location)
            print(parsed_location['spot'])
            retrieve_forecast(
                latitude=parsed_location['latitude'],
                longitude=parsed_location['longitude'],
                beach_direction=parsed_location['beach_direction'],
                ideal_swell_direction=parsed_location['ideal_swell_direction'],
                country=parsed_location['country'],
                region=parsed_location['region'],
                spot=parsed_location['spot'],
                forecastDate=forecastDate
            )
        
        
        return {
            'statusCode': 200,
            'body': json.dumps('Forecast data saved successfully!')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error retrieving or saving forecast data: {str(e)}')
        }