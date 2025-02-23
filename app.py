
import json
import os
import boto3
from services.forecast_service import *
from services.dynamodb_service import *

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['DYNAMODB_TABLE']

def lambda_handler(event, context):
    try:
        # Get location data first
        locations = get_location_data()
        forecast_data = []
        loops = 0
        # Get forecast for each location
        for location in locations:
            if loops == 1:
                break
            loops += 1
            parsed_location = parse_location_data(location)
            spot_forecast = retrieve_forecast(
                latitude=parsed_location['latitude'],
                longitude=parsed_location['longitude'],
                beach_direction=parsed_location['beach_direction'],
                ideal_swell_direction=parsed_location['ideal_swell_direction'],
                country=parsed_location['country'],
                region=parsed_location['region'],
                spot=parsed_location['spot']
            )
            forecast_data.extend(spot_forecast)
        
        # Save forecasts to DynamoDB
        table_name = os.environ['FORECAST_TABLE']
        for data in forecast_data:
            forecast_date = data['forecastDate']
            sort_key = f"{data['country']}_{data['region']}_{data['spot']}"
            save_forecast_data(table_name, forecast_date, sort_key, data)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Forecast data saved successfully!')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error retrieving or saving forecast data: {str(e)}')
        }