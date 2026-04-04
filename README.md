# TrebleSurf Forecaster

Fetches surf forecast data from StormGlass API and stores it in DynamoDB. Runs as an AWS Lambda function.

## Overview

This service pulls weather and wave data from StormGlass, runs some surf-specific calculations on it, and saves everything to DynamoDB so other parts of TrebleSurf can use it.

## Architecture

- Python 3.8+ running on AWS Lambda
- Gets data from StormGlass API
- Stores data in DynamoDB
- Can also run in Docker

## Project Structure

```
treblesurf-forecaster/
├── app.py                      # Main Lambda handler
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── services/
│   ├── __init__.py
│   ├── forecast_service.py     # StormGlass API integration
│   └── dynamodb_service.py     # DynamoDB operations
└── utils/
    ├── __init__.py
    └── calculations.py         # Surf-specific calculations
```

## Features

### Core Functionality

- Fetches 10-day surf forecasts for multiple locations from one or more sources per spot and time
- **StormGlass**: used for all spots (wind, met, and wave data)
- **Irish Marine Institute (IMI) SWAN**: wave model via [ERDDAP griddap](https://erddap.marine.ie/erddap/griddap/IMI_IRISH_SHELF_SWAN_WAVE.html), used for spots within the Irish shelf grid (lat 49–56°, lon -15° to -3°); wave-only, same calculations as StormGlass where applicable
- **Apple WeatherKit**: hourly weather (wind, precipitation, temperature, etc.) for all spots when configured; weather-only, same wind/surf-messiness calculations where applicable
- Collects air temperature, humidity, pressure, wind data, water temperature, swell height, period, and direction
- Calculates surf-related metrics:
  - Surf size estimation based on swell height, period, and beach direction
  - Wave energy calculations
  - Wind direction analysis (offshore, onshore, cross-shore)
  - Surf quality assessment (clean, okay, messy)
  - Swell direction quality scoring

### Data Processing

- Uses DynamoDB batch writes to save forecast data
- Converts float values to Decimal for DynamoDB compatibility
- Handles API failures and database errors

## What’s needed to make it work

### GitHub Secrets (for Lambda deploy)

Configure these in your repo **Settings → Secrets and variables → Actions** (or the environment used by the deploy workflow):

| Secret | Required | Description |
|--------|----------|-------------|
| `STORMGLASS_API_KEY` | Yes | StormGlass API key for forecast data. |
| `APPLE_TEAM_ID` | No (WeatherKit) | Apple Developer Team ID. |
| `APPLE_SERVICE_ID` | No (WeatherKit) | WeatherKit Service ID (e.g. `com.example.weatherkit`). |
| `APPLE_KEY_ID` | No (WeatherKit) | Key ID of the WeatherKit-capable Auth Key. |
| `APPLE_PRIVATE_KEY` | No (WeatherKit) | **Contents of your `.p8` file** (the whole file: the `-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----` block). Paste as one line with `\n` where the line breaks are, or paste with real newlines—both work. |
| `WEATHERKIT_JWT` | No (WeatherKit) | Alternative to the four `APPLE_*` secrets: a pre-generated JWT. Short-lived; for production the app generates JWTs from `APPLE_*` in Lambda. |

If `WEATHERKIT_JWT` is set, it is used. Otherwise, if all four `APPLE_*` secrets are set, the Lambda generates a JWT and fetches WeatherKit (wind, rain) **only inside IMI SWAN bounds**, merges with SWAN, and stores **`source=imi_swan+weatherkit`** (no standalone `weatherkit` rows). If none are set, that path is skipped.

**Using your `.p8` file:** Open the file (e.g. `AuthKey_XXXXXXXX.p8`), copy everything from `-----BEGIN PRIVATE KEY-----` through `-----END PRIVATE KEY-----`. For `APPLE_PRIVATE_KEY` you can either paste that block with real newlines, or as a single line with `\n` in place of each line break (e.g. `-----BEGIN PRIVATE KEY-----\nMIGT...\n-----END PRIVATE KEY-----\n`). `APPLE_KEY_ID` is the same as the filename’s ID part (e.g. `XXXXXXXX`).

**Backend:** The API that reads forecast data must support the new multi-source schema. See [docs/BACKEND_README.md](docs/BACKEND_README.md) for what to change.

## Installation & Setup

### Prerequisites

- Python 3.8+
- AWS CLI configured
- StormGlass API key
- AWS DynamoDB tables: `surf_forecasts` (or override via `FORECAST_TABLE`) and `LocationData`

### Local Development

1. Clone the repository

   ```bash
   git clone <repository-url>
   cd treblesurf-forecaster
   ```

2. Create virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables
   ```bash
   export STORMGLASS_API_KEY="your-api-key-here"
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="your-region"
   ```

### Docker Deployment

1. Build the container

   ```bash
   docker build -t treblesurf-forecaster .
   ```

2. Run locally
   ```bash
   docker run -p 5000:5000 treblesurf-forecaster
   ```

## Data Schema

### DynamoDB Tables

#### `surf_forecasts` Table

Multiple forecast sources use separate partition keys per source (e.g. StormGlass vs merged Irish shelf).

- Partition Key: `spot_id` (format: `country#region#spot#source`)
- Sort Key: `timestamp_ts` (Number, Unix seconds for `dateForecastedFor`)
- Attributes:
  - `generated_at`: When the forecast run was generated
  - `source`: Same identifier as the last segment of `spot_id` (`stormglass`, `imi_swan+weatherkit`, …)
  - `data`: Complete forecast data object

For migration and table creation, see [docs/SCHEMA_MIGRATION.md](docs/SCHEMA_MIGRATION.md). For how the backend API should read and expose multi-source data, see [docs/BACKEND_README.md](docs/BACKEND_README.md).

#### LocationData Table

- Partition Key: `country_region_spot` (format: `country/region/spot`)
- Attributes:
  - `Latitude`, `Longitude`: Geographic coordinates
  - `BeachDirection`: Beach orientation (degrees)
  - `IdealSwellDirection`: Optimal swell direction range

### Forecast Data Structure

```json
{
  "dateForecastedFor": "2024-01-15 12:00:00",
  "temperature": 15.5,
  "humidity": 75.2,
  "pressure": 1013.25,
  "windSpeed": 8.5,
  "precipitation": 0.0,
  "windDirection": 245.0,
  "waterTemperature": 12.8,
  "swellHeight": 1.2,
  "swellPeriod": 11.5,
  "swellDirection": 250.0,
  "surfSize": 1.08,
  "waveEnergy": 125.7,
  "relativeWindDirection": "Cross-off",
  "surfMessiness": "Clean",
  "directionQuality": 0.85
}
```

## Configuration

### Environment Variables

- `STORMGLASS_API_KEY`: Your StormGlass API key
- `FORECAST_TABLE`: DynamoDB forecast table name (default: `surf_forecasts`). Table must use `spot_id` (String) and `timestamp_ts` (Number); see [docs/SCHEMA_MIGRATION.md](docs/SCHEMA_MIGRATION.md).
- **WeatherKit** (optional): use one of:
  - `WEATHERKIT_JWT`: pre-generated JWT (short-lived; refresh as needed), or
  - Apple credentials for server-side JWT: `APPLE_TEAM_ID`, `APPLE_SERVICE_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` (PEM string; in Lambda use `\n` for newlines). Requires `pyjwt` and `cryptography`.
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (e.g., us-east-1)

### StormGlass API Parameters

The service fetches these weather parameters:

- `airTemperature`: Air temperature in Celsius
- `humidity`: Relative humidity percentage
- `pressure`: Atmospheric pressure in hPa
- `windSpeed`: Wind speed in m/s
- `precipitation`: Precipitation in mm
- `windDirection`: Wind direction in degrees
- `waterTemperature`: Sea surface temperature in Celsius
- `swellHeight`: Significant wave height in meters
- `swellPeriod`: Wave period in seconds
- `swellDirection`: Swell direction in degrees

## Surf Calculations

### Surf Size Calculation

Calculates expected surf size based on:

- Swell height and period
- Beach direction vs swell direction
- Period-based multipliers (0.55x to 1.3x)
- Direction wrap reduction factor

### Wave Energy

Computes wave energy using:

- Significant wave height (Hs)
- Wave period (T)
- Peak period (Tp)
- Spreading parameter (sigma)
- Gamma function

### Wind Analysis

- Offshore: Wind blowing from land to sea (cleanest conditions)
- Cross-off: Wind blowing diagonally offshore
- Cross-shore: Wind blowing parallel to shore
- Cross-on: Wind blowing diagonally onshore
- Onshore: Wind blowing from sea to land (messiest conditions)

### Surf Quality Assessment

Based on wind speed and direction:

- Clean: Good surfing conditions
- Okay: Decent surfing conditions
- Messy: Challenging surfing conditions

## Deployment

### AWS Lambda Deployment

1. Package the function

   ```bash
   zip -r function.zip . -x "venv/*" "*.git*"
   ```

2. Deploy using AWS CLI

   ```bash
   aws lambda create-function \
     --function-name treblesurf-forecaster \
     --runtime python3.8 \
     --role arn:aws:iam::account:role/lambda-execution-role \
     --handler app.lambda_handler \
     --zip-file fileb://function.zip
   ```

3. Set environment variables
   ```bash
   aws lambda update-function-configuration \
     --function-name treblesurf-forecaster \
     --environment Variables='{STORMGLASS_API_KEY=your-key}'
   ```

### Scheduled Execution

The deploy workflow creates EventBridge rules that invoke the same Lambda with different payloads:

| Rule | Schedule (UTC) | What runs |
|------|----------------|-----------|
| `surf-forecast-schedule` | 08:00, 19:00 daily | StormGlass for **non–in-bounds-Ireland** spots + Ireland outside IMI bounds; **no** StormGlass for Ireland inside IMI bounds (merged `imi_swan+weatherkit` only there) |
| `surf-forecast-weatherkit` | Every hour (:00) | Same merge path: fetches IMI + WeatherKit in bounds, writes **`imi_swan+weatherkit` only** |

The legacy `surf-forecast-imi` (6-hourly IMI-only) rule is removed on deploy; hourly IMI+WK replaces it.

The Lambda accepts an optional `sources` array in the event (e.g. `{"sources": ["imi_swan", "weatherkit"]}`) to run only those sources; with no `sources` it runs all.

## Testing

Run the main Lambda handler function to test forecast retrieval and data storage.

## Monitoring & Logging

### CloudWatch Logs

Check AWS CloudWatch Logs for:

- API response times
- DynamoDB operation success/failure
- Error messages and stack traces

### Metrics to Monitor

- Function duration
- Memory usage
- Error rate
- DynamoDB write capacity units

## Security

### API Key Management

- Store StormGlass API key in Github actions secrets
- Use IAM roles for Lambda execution
- Use least-privilege access policies

### Data Protection

- Data stored in DynamoDB is encrypted at rest
- API communications use HTTPS
- No sensitive data logged in CloudWatch

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is part of the TrebleSurf ecosystem. Please refer to the main TrebleSurf repository for licensing information.

## Support

For support and questions:

- Create an issue in the repository
- Contact the TrebleSurf development team
- Check the TrebleSurf documentation

## Related Projects

- treblesurf-backend: Main API server and WebSocket services
- treblesurf-buoyData: Buoy data collection and swell prediction service
- treblesurf-frontend: Web application interface
