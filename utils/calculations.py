def calculate_wave_energy(Hs, T, Tp=10, alpha=8.5):
    g = 9.81  # acceleration due to gravity in m/s^2
    sigma = 0.07 if T/Tp <= 1 else 0.09  # sigma is a spreading parameter
    gamma_alpha = 3.3 if alpha == 7 else 1.25 * alpha - 4.5  # gamma as a function of alpha
    
    exponent = -0.5 * ((Tp / T) ** 2)
    spectrum = 0.0623 * (g ** 2) * T * (Hs ** 2) * gamma_alpha ** math.exp(exponent)
    
    return spectrum

def calculate_surf_size(swell_height, swell_period, beach_direction, ideal_swell_direction):
    surf_size = 0
    difference = math.fabs(beach_direction - ideal_swell_direction)
    normalized_difference = min(difference, 360 - difference)
    
    wrap_amount = normalized_difference / 360
    wrap_reduction_factor = 1.4 - wrap_amount

    if swell_period <= 8:
        surf_size = swell_height * 0.55 * wrap_reduction_factor
    elif swell_period < 9:
        surf_size = swell_height * 0.6 * wrap_reduction_factor
    elif swell_period < 10:
        surf_size = swell_height * 0.7 * wrap_reduction_factor
    elif swell_period < 11:
        surf_size = swell_height * 0.8 * wrap_reduction_factor
    elif swell_period < 12:
        surf_size = swell_height * 0.9 * wrap_reduction_factor
    elif swell_period < 13:
        surf_size = swell_height * 1 * wrap_reduction_factor
    elif swell_period < 14:
        surf_size = swell_height * 1.1 * wrap_reduction_factor
    elif swell_period < 15:
        surf_size = swell_height * 1.2 * wrap_reduction_factor
    else:
        surf_size = swell_height * 1.3 * wrap_reduction_factor

    return surf_size * wrap_reduction_factor