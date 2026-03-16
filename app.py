import json
import os
import boto3
import arrow
from services.forecast_service import retrieve_forecast
from services.dynamodb_service import (
    get_location_data,
    migrate_old_forecast_items_to_multi_source,
    parse_location_data,
    save_forecast_data_batch,
)
from services.imi_erddap_service import fetch_imi_forecast, in_imi_bounds
from services.weatherkit_service import fetch_weatherkit_forecast

dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    # Optional: run only specific sources. Event: { "sources": ["stormglass", "imi_swan", "weatherkit"] } or omit for all.
    requested = event.get("sources")
    if requested is not None and not isinstance(requested, list):
        requested = None
    run_all = requested is None or len(requested) == 0
    run_stormglass = run_all or "stormglass" in requested
    run_imi = run_all or "imi_swan" in requested
    run_weatherkit = run_all or "weatherkit" in requested

    try:
        if run_stormglass:
            migrate_old_forecast_items_to_multi_source(max_items_per_run=100)

        locations = get_location_data()
        forecast_date = arrow.now().format('YYYY-MM-DD HH')
        for location in locations:
            print(forecast_date)
            print(location)
            parsed = parse_location_data(location)
            print(parsed['spot'])
            if run_stormglass:
                retrieve_forecast(
                    latitude=parsed['latitude'],
                    longitude=parsed['longitude'],
                    beach_direction=parsed['beach_direction'],
                    ideal_swell_direction=parsed['ideal_swell_direction'],
                    country=parsed['country'],
                    region=parsed['region'],
                    spot=parsed['spot'],
                    forecastDate=forecast_date,
                )
            if run_imi and in_imi_bounds(parsed['latitude'], parsed['longitude']):
                imi_data = fetch_imi_forecast(
                    latitude=parsed['latitude'],
                    longitude=parsed['longitude'],
                    beach_direction=parsed['beach_direction'],
                    ideal_swell_direction=parsed['ideal_swell_direction'],
                )
                if imi_data:
                    save_forecast_data_batch(
                        imi_data,
                        forecast_date,
                        parsed['country'],
                        parsed['region'],
                        parsed['spot'],
                        source='imi_swan',
                    )
            if run_weatherkit:
                weatherkit_data = fetch_weatherkit_forecast(
                    latitude=parsed['latitude'],
                    longitude=parsed['longitude'],
                    beach_direction=parsed['beach_direction'],
                )
                if weatherkit_data:
                    save_forecast_data_batch(
                        weatherkit_data,
                        forecast_date,
                        parsed['country'],
                        parsed['region'],
                        parsed['spot'],
                        source='weatherkit',
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