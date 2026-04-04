import json
import os
import boto3
import arrow
from services.forecast_service import retrieve_forecast
from services.dynamodb_service import (
    get_location_data,
    parse_location_data,
    save_forecast_data_batch,
)
from services.imi_erddap_service import fetch_imi_forecast, in_imi_bounds
from services.merge_ireland_primary import merge_ireland_swan_weatherkit
from services.weatherkit_service import fetch_weatherkit_forecast

dynamodb = boto3.resource('dynamodb')


def _is_ireland(country):
    return (country or "").strip().lower() == "ireland"


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
        locations = get_location_data()
        forecast_date = arrow.now().format('YYYY-MM-DD HH')
        for location in locations:
            print(forecast_date)
            print(location)
            parsed = parse_location_data(location)
            print(parsed['spot'])
            in_bounds = in_imi_bounds(parsed['latitude'], parsed['longitude'])
            # Irish shelf spots use merged imi_swan+weatherkit only — skip Stormglass so Dynamo has ~1 row/hour
            # (not stormglass + merged). Ireland outside IMI bounds still gets Stormglass.
            if run_stormglass and not (_is_ireland(parsed['country']) and in_bounds):
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
            imi_data = None
            if run_imi and in_bounds:
                imi_data = fetch_imi_forecast(
                    latitude=parsed['latitude'],
                    longitude=parsed['longitude'],
                    beach_direction=parsed['beach_direction'],
                    ideal_swell_direction=parsed['ideal_swell_direction'],
                )
            weatherkit_data = None
            # WeatherKit is only fetched in IMI bounds; we persist merged `imi_swan+weatherkit` only (no standalone WK rows).
            if run_weatherkit and in_bounds:
                weatherkit_data = fetch_weatherkit_forecast(
                    latitude=parsed['latitude'],
                    longitude=parsed['longitude'],
                    beach_direction=parsed['beach_direction'],
                )
            # Pre-merged Ireland primary: swell from SWAN, weather from WeatherKit (only non-Stormglass source for Irish shelf).
            if imi_data and weatherkit_data:
                merged_primary = merge_ireland_swan_weatherkit(imi_data, weatherkit_data)
                if merged_primary:
                    save_forecast_data_batch(
                        merged_primary,
                        forecast_date,
                        parsed['country'],
                        parsed['region'],
                        parsed['spot'],
                        source='imi_swan+weatherkit',
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