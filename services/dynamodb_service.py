import os
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('FORECAST_TABLE', 'surf_forecasts')
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


def save_forecast_data_batch(formatted_data, forecast_date, country, region, spot, source='stormglass'):
    """
    Save all forecast data in a batch. Partition key is country#region#spot#source;
    sort key timestamp_ts is Unix seconds for dateForecastedFor.
    """
    epoch_timestamp = int(datetime.fromisoformat(forecast_date.replace('Z', '+00:00')).timestamp())
    try:
        with table.batch_writer() as batch:
            for data in formatted_data:
                spot_id = f"{country}#{region}#{spot}#{source}"
                forecast_ts = int(datetime.fromisoformat(data['dateForecastedFor'].replace('Z', '+00:00')).timestamp())

                item = {
                    'spot_id': spot_id,
                    'timestamp_ts': forecast_ts,
                    'generated_at': str(epoch_timestamp),
                    'source': source,
                    'data': convert_floats_to_decimal(data),
                }
                batch.put_item(Item=item)
    except ClientError as e:
        err = e.response.get("Error", {})
        if err.get("Code") == "ValidationException" and "key element does not match the schema" in (err.get("Message") or ""):
            print(
                "Error saving data to DynamoDB: Key does not match table schema. "
                "The forecast table must have partition key 'spot_id' (String) and sort key 'timestamp_ts' (Number). "
                "Create the table (see scripts/create_forecast_table.sh) and set FORECAST_TABLE."
            )
        else:
            print(f"Error saving data to DynamoDB: {e}")
    except Exception as e:
        print(f"Error saving data to DynamoDB: {e}")

    print("Batch save successful!")
    return


def get_location_data(table_name='LocationData'):
    """Fetch all surf spot locations from DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    loc_table = dynamodb.Table(table_name)

    response = loc_table.scan()
    locations = response['Items']

    while 'LastEvaluatedKey' in response:
        response = loc_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        locations.extend(response['Items'])

    return locations


def parse_location_data(location):
    """Parse location data into required format"""
    country_region_spot = location['country_region_spot']
    parts = country_region_spot.split('/')

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
