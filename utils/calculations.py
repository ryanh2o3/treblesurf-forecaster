import math 

def calculate_wave_energy(Hs, T, Tp=10, alpha=8.5):
    g = 9.81  # acceleration due to gravity in m/s^2
    sigma = 0.07 if T/Tp <= 1 else 0.09  # sigma is a spreading parameter
    gamma_alpha = 3.3 if alpha == 7 else 1.25 * alpha - 4.5  # gamma as a function of alpha
    
    exponent = -0.5 * ((Tp / T) ** 2)
    spectrum = 0.0623 * (g ** 2) * T * (Hs ** 2) * gamma_alpha ** math.exp(exponent)
    
    return spectrum

def calculate_surf_size(swell_height, swell_period, beach_direction, swell_direction):
    surf_size = 0
    difference = math.fabs(swell_direction - beach_direction)
    normalized_difference = min(difference, 360 - difference)
    
    wrap_amount = normalized_difference / 360
    wrap_reduction_factor = 1.4 - wrap_amount

    if swell_period <= 8:
        surf_size = swell_height * 0.55
    elif swell_period < 9:
        surf_size = swell_height * 0.6
    elif swell_period < 10:
        surf_size = swell_height * 0.7
    elif swell_period < 11:
        surf_size = swell_height * 0.8
    elif swell_period < 12:
        surf_size = swell_height * 0.9
    elif swell_period < 13:
        surf_size = swell_height * 1
    elif swell_period < 14:
        surf_size = swell_height * 1.1
    elif swell_period < 15:
        surf_size = swell_height * 1.2
    else:
        surf_size = swell_height * 1.3

    return surf_size * wrap_reduction_factor

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
        
def calculateRelativeWindDirection(windDirection, beachDirection):
    adjustedBeachDirection = (beachDirection +180) % 360
    difference = math.fabs(windDirection - adjustedBeachDirection)

    normalizedDifference = min(difference, 360 - difference)

    if normalizedDifference < 22.5:
        return 'Offshore'
    elif normalizedDifference < 67.5:
        return 'Cross-off'
    elif normalizedDifference < 112.5:
        return 'Cross'
    elif normalizedDifference < 157.5:
        return 'Cross-on'
    else:
        return 'Onshore'