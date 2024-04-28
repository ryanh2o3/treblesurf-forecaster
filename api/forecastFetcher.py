import firebase_admin
import os
import arrow
import requests
import math
from firebase_admin import credentials, initialize_app, db


# Initialize the Firebase Admin SDK with the secret value
cred = os.environ.get('DATABASE_ACCESS')

firebase_admin.initialize_app(cred, {'databaseURL': 'https://surfeable-default-rtdb.europe-west1.firebasedatabase.app/'})

def jonswap_spectrum(Hs, T, Tp=10, alpha=8.5):
    g = 9.81  # acceleration due to gravity in m/s^2
    sigma = 0.07 if T/Tp <= 1 else 0.09  # sigma is a spreading parameter
    gamma_alpha = 3.3 if alpha == 7 else 1.25 * alpha - 4.5  # gamma as a function of alpha
    
    exponent = -0.5 * ((Tp / T) ** 2)
    spectrum = 0.0623 * (g ** 2) * T * (Hs ** 2) * gamma_alpha ** math.exp(exponent)
    
    return spectrum

#function that loops through all the locations from the surfData databse and retrieves the 5 day forecast for each location placing the data into the surfData database
def retrieveForecast():

    #get all the locations from the database
    locations = getLocations()
    forecastDate = arrow.now().format('YYYY-MM-DD HH:mm:ss')

    # loop through each country
    for country, regions in locations.items():
        # loop through each region in the country
        for region, spots in regions.items():
            # loop through each spot in the region
            for spot, details in spots.items():
                # get the latitude and longitude of the spot
                latitude = details['Latitude']
                longitude = details['Longitude']

                beachDirection = details['BeachDirection']
                idealSwellDirection = details['IdealSwellDirection']

                # retrieve the 5 day forecast for the spot
                forecast = retrieve5DayWeather(latitude, longitude)
                # format the forecast data
                formattedForecast = formatForecast(forecast)
                # insert the formatted forecast data into the database
                insertForecast(formattedForecast, details['Name'], region, country, forecastDate, beachDirection, idealSwellDirection)
    


#function that retrieves all the locations from the Location node and its subfolders in the Firebase Realtime Database
def getLocations():
    #get a reference to the Location node
    locations_ref = db.reference('Location')
    #get all the locations from the database
    locations = locations_ref.order_by_key().get()
    #return the locations as a dictionary
    return dict(locations)

#function that inserts the forecast data into the database for a specific location
def insertForecast(forecast, spot, region, country, forecastDate, beachDirection, idealSwellDirection):
    #get the current date and time

    # Add the formatted forecast data to the WeatherData node in Firebase Realtime Database
    ref = db.reference('WeatherData/' + forecastDate + '/' + country + '/' + region + '/' + spot)
    for hour in forecast:
        ref.push().set({
            'forecastDate': hour['forecastDate'],
            'dateForecastedFor': hour['dateForecastedFor'],
            'Temperature': hour['temperature'],
            'Humidity': hour['humidity'],
            'Pressure': hour['pressure'],
            'WindSpeed': hour['windSpeed'],
            'Precipitation': hour['precipitation'],
            'WindDirection': hour['windDirection'],
            'WaterTemperature': hour['waterTemperature'],
            'SwellHeight': hour['swellHeight'],
            'SwellPeriod': hour['swellPeriod'],
            'SwellDirection': hour['swellDirection'],
            'SecondarySwellHeight': hour['secondarySwellHeight'],
            'SecondarySwellPeriod': hour['secondarySwellPeriod'],
            'SecondarySwellDirection': hour['secondarySwellDirection'],
            'WaveEnergy': jonswap_spectrum(hour['swellHeight'], hour['swellPeriod']),
            'RelativeWindDirection': calculateRelativeWindDirection(hour['windDirection'], beachDirection),
            'SurfMessiness': calculateSurfMessiness(hour['windSpeed'], hour['windDirection'], beachDirection),
            'SurfSize': calculateSurfSize(hour['swellHeight'], hour['swellPeriod'], hour['swellDirection'], beachDirection, idealSwellDirection),
            'DirectionQuality': calculateDirectionQuality(hour['swellDirection'], idealSwellDirection)
        })


#function that formats the forecast data which is in json and have hourly format 
def formatForecast(forecast):
    #create an empty list to store the formatted forecast data
    formattedForecast = []
    #loop through each hour of the forecast
    for hour in forecast['hours']:
        #create an empty dictionary to store the formatted data for each hour
        formattedHour = {}
        #get the date and time of the forecast which is now
        forecastDate = arrow.now().format('YYYY-MM-DD HH:mm:ss')
        #get the date and time the forecast is for
        dateForecastedFor = arrow.get(hour['time']).format('YYYY-MM-DD HH:mm:ss')
        #get the temperature
        temperature = hour['airTemperature']['sg']
        #get the humidity
        humidity = hour['humidity']['sg']
        #get the pressure
        pressure = hour['pressure']['sg']
        #get the wind speed
        windSpeed = hour['windSpeed']['sg']
        #get the precipitation
        precipitation = hour['precipitation']['sg']
        #get the wind direction
        windDirection = hour['windDirection']['sg']
        #get the water temperature
        waterTemperature = hour['waterTemperature']['sg']
        #get the swell height
        swellHeight = hour['swellHeight']['noaa']
        #get the swell period
        swellPeriod = hour['swellPeriod']['noaa']
        #get the swell direction
        swellDirection = hour['swellDirection']['noaa']
        #get the secondary swell height
        secondarySwellHeight = hour['secondarySwellHeight']['noaa']
        #get the secondary swell period
        secondarySwellPeriod = hour['secondarySwellPeriod']['noaa']
        #get the secondary swell direction
        secondarySwellDirection = hour['secondarySwellDirection']['noaa']
 
        #add the formatted data to the dictionary
        formattedHour['forecastDate'] = forecastDate
        formattedHour['dateForecastedFor'] = dateForecastedFor
        formattedHour['temperature'] = temperature
        formattedHour['humidity'] = humidity
        formattedHour['pressure'] = pressure
        formattedHour['windSpeed'] = windSpeed
        formattedHour['precipitation'] = precipitation
        formattedHour['windDirection'] = windDirection
        formattedHour['waterTemperature'] = waterTemperature
        formattedHour['swellHeight'] = swellHeight
        formattedHour['swellPeriod'] = swellPeriod
        formattedHour['swellDirection'] = swellDirection
        formattedHour['secondarySwellHeight'] = secondarySwellHeight
        formattedHour['secondarySwellPeriod'] = secondarySwellPeriod
        formattedHour['secondarySwellDirection'] = secondarySwellDirection
 
        #add the formatted data to the list
        formattedForecast.append(formattedHour)
    #return the formatted forecast data
    return formattedForecast


def retrieve5DayWeather(latitude, longitude):
  start = arrow.now()
  end = arrow.now().shift(days=+10).ceil('day')

  response = requests.get(
    'https://api.stormglass.io/v2/weather/point',
    params={
      'lat': latitude,
      'lng': longitude,
      'params': ','.join(['airTemperature', 'humidity', 'pressure', 'windSpeed', 'precipitation', 'windDirection', 'waterTemperature', 'swellHeight', 'swellPeriod', 'swellDirection', 'secondarySwellHeight', 'secondarySwellPeriod', 'secondarySwellDirection']),
      'start': start.to('UTC').timestamp(),  # Convert to UTC timestamp
      'end': end.to('UTC').timestamp()  # Convert to UTC timestamp
    },
    headers={
      'Authorization': '40b76f9e-28e6-11ee-8d52-0242ac130002-40b7702a-28e6-11ee-8d52-0242ac130002'
    }
  )
  json_data = response.json()
  return response.json()




def calculateRelativeWindDirection(windDirection, beachDirection):
    difference = math.fabs(windDirection - beachDirection)

    normalizedDifference = min(difference, 360 - difference)

    if normalizedDifference < 22.5:
        return 'Offshore'
    elif normalizedDifference < 67.5:
        return 'Cross-off'
    elif normalizedDifference < 112.5:
        return 'Cross-shore'
    elif normalizedDifference < 157.5:
        return 'Cross-on'
    else:
        return 'Onshore'
    
def calculateSurfMessiness(windSpeedIn, windDirection, beachDirection):
    relativeWindDirection = calculateRelativeWindDirection(windDirection, beachDirection)
    windSpeed = windSpeedIn * 3.6
    if relativeWindDirection == 'Offshore':
        if windSpeed < 30:
            return 'Clean'
        else:
            return 'Okay'
    elif relativeWindDirection == 'Cross-off':
        if windSpeed < 20:
            return 'Clean'
        elif windSpeed < 40:
            return 'Okay'
        else:
            return 'Messy'
    elif relativeWindDirection == 'Cross-shore':
        if windSpeed < 10:
            return 'Clean'
        elif windSpeed < 20:
            return 'Okay'
        else:
            return 'Messy'
    elif relativeWindDirection == 'Cross-on':
        if windSpeed < 5:
            return 'Clean'
        elif windSpeed < 15:
            return 'Okay'
        else:
            return 'Messy'
    else:
        if windSpeed < 5:
            return 'Clean'
        elif windSpeed < 10:
            return 'Okay'
        else:
            return 'Messy'
    

def calculateSurfSize(swellHeight, swellPeriod, swellDirection, beachDirection, idealSwellDirection):
    surfSize = 0

    difference = math.fabs(swellDirection - beachDirection)

    normalizedDifference = min(difference, 360 - difference)

    wrapAmount  = normalizedDifference / 360

    wrapReductionFactor = 1 - wrapAmount

    low, high = idealSwellDirection

    # Adjust the angles to fall within the same 180 degree range
    if high - low > 180:
        low += 360

    # Calculate the middle angle
    middle = (low + high) / 2

    # Normalize the middle angle to fall within the 0 to 360 degree range
    middle %= 360

    # Calculate the standard deviation
    std_dev = abs(high - low) / 1.5

    # Calculate the value of the Gaussian function
    directionSize = math.exp(-0.5 * ((swellDirection - middle) / std_dev) ** 2) 


    if swellPeriod <= 8:
        surfSize =  swellHeight * 0.55 * wrapReductionFactor
    elif swellPeriod < 9:
        surfSize =  swellHeight * 0.6 * wrapReductionFactor
    elif swellPeriod < 10:
        surfSize =  swellHeight * 0.7 * wrapReductionFactor
    elif swellPeriod < 11:
        surfSize =  swellHeight * 0.8 * wrapReductionFactor
    elif swellPeriod < 12:
        surfSize =  swellHeight * 0.9 * wrapReductionFactor
    elif swellPeriod < 13:
        surfSize =  swellHeight * 1 * wrapReductionFactor
    elif swellPeriod < 14:
        surfSize =  swellHeight * 1.1 * wrapReductionFactor
    elif swellPeriod < 15:
        surfSize = swellHeight * 1.2 * wrapReductionFactor
    else:
        surfSize =  swellHeight * 1.3 * wrapReductionFactor

    return surfSize * wrapReductionFactor * directionSize


def calculateDirectionQuality(swellDirection, idealSwellDirection):
    low, high = idealSwellDirection

    # Adjust the angles to fall within the same 180 degree range
    if high - low > 180:
        low += 360

    # Calculate the middle angle
    middle = (low + high) / 2

    # Normalize the middle angle to fall within the 0 to 360 degree range
    middle %= 360

    # Calculate the standard deviation
    std_dev = abs(high - low) / 2.5

    # Calculate the value of the Gaussian function
    directionQuality = math.exp(-0.5 * ((swellDirection - middle) / std_dev) ** 2) 

    return directionQuality
    
