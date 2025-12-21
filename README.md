# TrebleSurf Forecaster

A serverless AWS Lambda function that fetches surf forecast data from StormGlass API and stores it in DynamoDB for surf spot predictions and analysis.

## 🌊 Overview

The TrebleSurf Forecaster is a Python-based AWS Lambda function designed to automatically collect and process surf forecast data for multiple surf spots. It retrieves weather and oceanographic data from the StormGlass API, performs surf-specific calculations, and stores the processed data in DynamoDB for use by other TrebleSurf applications.

## 🏗️ Architecture

- **Runtime**: Python 3.8+ (AWS Lambda)
- **Data Source**: StormGlass API
- **Storage**: AWS DynamoDB
- **Deployment**: AWS Lambda (serverless)
- **Containerization**: Docker support available

## 📁 Project Structure

```
treblesurf-forecaster/
├── app.py                      # Main Lambda handler
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── services/
│   ├── __init__.py
│   ├── forecast_service.py     # StormGlass API integration
│   └── dynamodb_service.py     # DynamoDB operations
├── utils/
│   ├── __init__.py
│   └── calculations.py         # Surf-specific calculations
└── templates/
    └── index.html              # Basic HTML template
```

## 🚀 Features

### Core Functionality

- **Automated Forecast Collection**: Fetches 10-day surf forecasts for multiple locations
- **Multi-Parameter Data**: Collects air temperature, humidity, pressure, wind data, water temperature, swell height, period, and direction
- **Surf-Specific Calculations**:
  - Surf size estimation based on swell height, period, and beach direction
  - Wave energy calculations
  - Wind direction analysis (offshore, onshore, cross-shore)
  - Surf quality assessment (clean, okay, messy)
  - Swell direction quality scoring

### Data Processing

- **Batch Operations**: Efficiently saves forecast data using DynamoDB batch writes
- **Data Validation**: Converts float values to Decimal for DynamoDB compatibility
- **Error Handling**: Comprehensive error handling for API failures and database operations

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- AWS CLI configured
- StormGlass API key
- AWS DynamoDB tables: `SpotForecastData` and `LocationData`

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd treblesurf-forecaster
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**
   ```bash
   export STORMGLASS_API_KEY="your-api-key-here"
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="your-region"
   ```

### Docker Deployment

1. **Build the container**

   ```bash
   docker build -t treblesurf-forecaster .
   ```

2. **Run locally**
   ```bash
   docker run -p 5000:5000 treblesurf-forecaster
   ```

## 📊 Data Schema

### DynamoDB Tables

#### SpotForecastData Table

- **Partition Key**: `spot_id` (format: `country#region#spot`)
- **Sort Key**: `forecast_timestamp` (Unix timestamp)
- **Attributes**:
  - `generated_at`: When the forecast was generated
  - `data`: Complete forecast data object

#### LocationData Table

- **Partition Key**: `country_region_spot` (format: `country/region/spot`)
- **Attributes**:
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

## 🔧 Configuration

### Environment Variables

- `STORMGLASS_API_KEY`: Your StormGlass API key
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (e.g., us-east-1)

### StormGlass API Parameters

The service fetches the following weather parameters:

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

## 🧮 Surf Calculations

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

- **Offshore**: Wind blowing from land to sea (cleanest conditions)
- **Cross-off**: Wind blowing diagonally offshore
- **Cross-shore**: Wind blowing parallel to shore
- **Cross-on**: Wind blowing diagonally onshore
- **Onshore**: Wind blowing from sea to land (messiest conditions)

### Surf Quality Assessment

Based on wind speed and direction:

- **Clean**: Optimal surfing conditions
- **Okay**: Decent surfing conditions
- **Messy**: Challenging surfing conditions

## 🚀 Deployment

### AWS Lambda Deployment

1. **Package the function**

   ```bash
   zip -r function.zip . -x "venv/*" "*.git*"
   ```

2. **Deploy using AWS CLI**

   ```bash
   aws lambda create-function \
     --function-name treblesurf-forecaster \
     --runtime python3.8 \
     --role arn:aws:iam::account:role/lambda-execution-role \
     --handler app.lambda_handler \
     --zip-file fileb://function.zip
   ```

3. **Set environment variables**
   ```bash
   aws lambda update-function-configuration \
     --function-name treblesurf-forecaster \
     --environment Variables='{STORMGLASS_API_KEY=your-key}'
   ```

### Scheduled Execution

Set up CloudWatch Events to trigger the function on a schedule:

```bash
aws events put-rule \
  --name treblesurf-forecaster-schedule \
  --schedule-expression "rate(6 hours)"
```

## 🧪 Testing

### Running Tests

Run the main Lambda handler function for testing forecast retrieval and data storage.

## 📈 Monitoring & Logging

### CloudWatch Logs

Monitor function execution through AWS CloudWatch Logs:

- API response times
- DynamoDB operation success/failure
- Error messages and stack traces

### Metrics to Monitor

- Function duration
- Memory usage
- Error rate
- DynamoDB write capacity units

## 🔒 Security

### API Key Management

- Store StormGlass API key in AWS Systems Manager Parameter Store
- Use IAM roles for Lambda execution
- Implement least-privilege access policies

### Data Protection

- All data stored in DynamoDB is encrypted at rest
- API communications use HTTPS
- No sensitive data logged in CloudWatch

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is part of the TrebleSurf ecosystem. Please refer to the main TrebleSurf repository for licensing information.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Contact the TrebleSurf development team
- Check the TrebleSurf documentation

## 🔄 Related Projects

- **treblesurf-backend**: Main API server and WebSocket services
- **treblesurf-buoyData**: Buoy data collection and swell prediction service
- **treblesurf-frontend**: Web application interface

---

_Built with ❤️ for the surfing community_
