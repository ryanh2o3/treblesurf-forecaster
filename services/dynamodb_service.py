import boto3
from botocore.exceptions import ClientError
import json
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = 'SpotForecastData'
table = dynamodb.Table(table_name)


def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def save_forecast_data(forecast_data, forecast_date, sort_key):
    print(sort_key)
    item = {
        'forecastDate': forecast_date,
        'country_region_spot': f"{sort_key}#{forecast_data['dateForecastedFor']}", # Make unique composite key
        'data': convert_floats_to_decimal(forecast_data)
    }
    
    try:
        table.put_item(Item=item)
        return True
    except ClientError as e:
        print(f"Error saving data to DynamoDB: {e.response['Error']['Message']}")
        return False

def save_forecast_data_batch(formatted_data, forecast_date, country, region, spot):
    """
    Save all forecast data in a batch.
    """
    # Convert forecast_date to epoch timestamp
    epoch_timestamp = int(datetime.fromisoformat(forecast_date.replace('Z', '+00:00')).timestamp())
    try: 
        with table.batch_writer() as batch:
            for data in formatted_data:
                # Construct the partition key and sort key
                spot_id = f"{country}#{region}#{spot}"
                forecast_timestamp = int(datetime.fromisoformat(data['dateForecastedFor'].replace('Z', '+00:00')).timestamp())
                generated_at = epoch_timestamp
                
                # The sort key is a compound of forecastDate and generatedAt
                sort_key = f"{forecast_timestamp}#{generated_at}"
                
                # Construct the item to be saved
                item = {
                    'spot_id': spot_id,  # Use the spot_id as partition key
                    'forecast_timestamp#generated_at': sort_key,  # The compound sort key
                    'generated_at': generated_at,  # Store the generated_at timestamp
                    'data': convert_floats_to_decimal(data)  # Store the data as a JSON object
                }
                # Put item in the batch
                batch.put_item(Item=item)
    except Exception as e:
        print(f"Error saving data to DynamoDB: {e}")          
                
    
    print("Batch save successful!")
    return


def get_location_data(table_name='LocationData'):
    """Fetch all surf spot locations from DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    response = table.scan()
    locations = response['Items']
    
    # Handle pagination if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        locations.extend(response['Items'])
    
    return locations

def parse_location_data(location):
    """Parse location data into required format"""
    country_region_spot = location['country_region_spot']
    parts = country_region_spot.split('/')
    
    # Parse IdealSwellDirection string into tuple
    ideal_swell = location['IdealSwellDirection'].strip('"').split(',')
    ideal_swell = (float(ideal_swell[0]), float(ideal_swell[1]))
    
    return {
        'country': parts[0],
        'region': parts[1],
        'spot': parts[2],
        'beach_direction': float(location['BeachDirection']),
        'latitude': float(location['Latitude']),
        'longitude': float(location['Longitude']),
        'ideal_swell_direction': ideal_swell
    }