
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
        for location in locations:
            parsed_location = parse_location_data(location)
            retrieve_forecast(
                latitude=parsed_location['latitude'],
                longitude=parsed_location['longitude'],
                beach_direction=parsed_location['beach_direction'],
                ideal_swell_direction=parsed_location['ideal_swell_direction'],
                country=parsed_location['country'],
                region=parsed_location['region'],
                spot=parsed_location['spot']
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