import os
import boto3
from botocore.exceptions import ClientError
import json
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('FORECAST_TABLE', 'SpotForecastData')
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

def save_forecast_data_batch(formatted_data, forecast_date, country, region, spot, source='stormglass'):
    """
    Save all forecast data in a batch. Supports multiple sources per spot and time
    via composite sort key forecast_timestamp#source.
    """
    # Convert forecast_date to epoch timestamp
    epoch_timestamp = int(datetime.fromisoformat(forecast_date.replace('Z', '+00:00')).timestamp())
    try:
        with table.batch_writer() as batch:
            for data in formatted_data:
                spot_id = f"{country}#{region}#{spot}"
                forecast_ts = int(datetime.fromisoformat(data['dateForecastedFor'].replace('Z', '+00:00')).timestamp())
                # Composite sort key so multiple sources can exist for same spot and time
                sort_key = f"{forecast_ts}#{source}"

                item = {
                    'spot_id': spot_id,
                    'forecast_timestamp': sort_key,
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
                "The forecast table must have partition key 'spot_id' (String) and sort key 'forecast_timestamp' (String). "
                "If your table was created with sort key as Number, create a new table with sort key as String and set FORECAST_TABLE."
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


def migrate_old_forecast_items_to_multi_source(max_items_per_run=500):
    """
    Find forecast items in the old format (sort key = timestamp only, no 'source' attribute),
    write them in the new format (sort key = timestamp#stormglass, source = 'stormglass'),
    then delete the old items. Runs at the start of every invocation with a per-run limit
    to avoid timeout; with many scheduled runs per day (full + WeatherKit hourly, etc.),
    a large backlog will clear over time. Uses known spot_ids from LocationData.
    Returns the number of items migrated this run.
    """
    try:
        locations = get_location_data()
    except Exception as e:
        print(f"Migration: could not load locations: {e}")
        return 0

    spot_ids = []
    for loc in locations:
        parsed = parse_location_data(loc)
        spot_ids.append(f"{parsed['country']}#{parsed['region']}#{parsed['spot']}")
    spot_ids = list(dict.fromkeys(spot_ids))  # dedupe

    migrated = 0
    for spot_id in spot_ids:
        if migrated >= max_items_per_run:
            break
        try:
            response = table.query(
                KeyConditionExpression="spot_id = :sid",
                ExpressionAttributeValues={":sid": spot_id},
            )
        except ClientError as e:
            print(f"Migration: query failed for {spot_id}: {e}")
            continue

        for item in response.get("Items", []):
            if migrated >= max_items_per_run:
                break
            sort_key = item.get("forecast_timestamp") or ""
            if "#" in sort_key or item.get("source") is not None:
                continue
            try:
                new_sort_key = f"{sort_key}#stormglass"
                new_item = {
                    "spot_id": item["spot_id"],
                    "forecast_timestamp": new_sort_key,
                    "generated_at": item["generated_at"],
                    "source": "stormglass",
                    "data": item["data"],
                }
                table.put_item(Item=new_item)
                table.delete_item(
                    Key={
                        "spot_id": item["spot_id"],
                        "forecast_timestamp": sort_key,
                    }
                )
                migrated += 1
            except ClientError as e:
                print(f"Migration: put/delete failed for {spot_id} {sort_key}: {e}")
                continue

        while response.get("LastEvaluatedKey") and migrated < max_items_per_run:
            response = table.query(
                KeyConditionExpression="spot_id = :sid",
                ExpressionAttributeValues={":sid": spot_id},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                if migrated >= max_items_per_run:
                    break
                sort_key = item.get("forecast_timestamp") or ""
                if "#" in sort_key or item.get("source") is not None:
                    continue
                try:
                    new_sort_key = f"{sort_key}#stormglass"
                    new_item = {
                        "spot_id": item["spot_id"],
                        "forecast_timestamp": new_sort_key,
                        "generated_at": item["generated_at"],
                        "source": "stormglass",
                        "data": item["data"],
                    }
                    table.put_item(Item=new_item)
                    table.delete_item(
                        Key={
                            "spot_id": item["spot_id"],
                            "forecast_timestamp": sort_key,
                        }
                    )
                    migrated += 1
                except ClientError as e:
                    print(f"Migration: put/delete failed for {spot_id} {sort_key}: {e}")

    if migrated > 0:
        print(f"Migration: migrated {migrated} old-format items to multi-source format")
    return migrated