import numpy as np
import math
import pandas as pd

def clean_na(series, how = 'drop'):
    if how == 'drop':
        series.dropna(inplace=True)
    elif how == 'fill':
        series = series.fillna(method ='ffill')
    return series

def exponential_smoothing(series, alpha = 0.5):
    '''
        Input:
            series - pandas series with timestamps
            alpha - float [0.0, 1.0], smoothing parameter
        Output: 
            smoothed series
    '''
    result = [series[0]] # first value is same as series
    for n in range(1, len(series)):
        result.append(alpha * series[n] + (1 - alpha) * result[n-1])
    return result

def box_convolution(series, box_pts):
    '''
        Implements 1-d square-box filtering on an input signal, using padding on both sides of the signal
        series: pandas series
        box_pts: must be an odd number
    '''
    
    half_window = (box_pts -1) // 2
    try:
        box = np.ones(box_pts)/box_pts
        firstvals = series[0] - np.abs( series[1:half_window+1][::-1] - series[0] )
        lastvals = series[-1] + np.abs(series[-half_window-1:-1][::-1] - series[-1])
        series = np.concatenate((firstvals, list(map(float, series)), lastvals))
        series_smooth = np.convolve(series, box, mode='valid')
        return series_smooth
    except:
        pass
    return np.ones(len(series))

def derivative(y, x):
    dx = np.zeros(x.shape, np.float)
    dy = np.zeros(y.shape, np.float)
    
    if isinstance(x, pd.DatetimeIndex):
        print ('x is of type DatetimeIndex')
        
        for i in range(len(x)-1):
            dx[i] =  (x[i+1]-x[i]).seconds
            
        dx [-1] = np.inf
    else:
        dx = np.diff(x)

    dy[0:-1] = np.diff(y)/dx[0:-1]
    dy[-1] = (y[-1] - y[-2])/dx[-1]
    result = dy
    return result

def time_derivative(series, window = 1):

    return series.diff(periods = window)/(2*series.index.to_series().diff(periods = window).dt.total_seconds())

def time_diff(series, window = 1):
    return series.index.to_series().diff(periods = window).dt.total_seconds()

def gradient(series, raster):
    return np.gradient(series, raster*2)

def absolute_humidity(temperature, rel_humidity, pressure):
    '''
        Calculate Absolute humidity based on vapour equilibrium:
        Input: 
            Temperature: in degC
            Rel_humidity: in %
            Pressure: in mbar
        Output:
            Absolute_humidity: in mg/m3?
    '''
    # Vapour equilibrium: 
    # _Temp is temperature in degC, _Press is absolute pressure in mbar
    vap_eq = (1.0007 + 3.46*1e-6*pressure)*6.1121*np.exp(17.502*temperature/(240.97+temperature))

    abs_humidity = rel_humidity * vap_eq

    return abs_humidity

def maxer(series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<=val and not series[i] == np.nan): result[i] = val
        elif (series[i]>val and not series[i] == np.nan): result[i] = series[i]
        elif (math.isnan(series[i])): result[i] = np.nan
    return result

def maxer_hist(series, val, hist):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<=val and not series[i] == np.nan): result[i] = hist
        elif (series[i]>val and not series[i] == np.nan): result[i] = series[i]
        elif (math.isnan(series[i])): result[i] = np.nan
    return result

def miner(series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<=val and not series[i] == np.nan): result[i] = series[i]
        elif (series[i]>val and not series[i] == np.nan): result[i] = val
        elif (math.isnan(series[i])): result[i] = np.nan
    return result

def greater(series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<=val and not series[i] == np.nan): result[i] = False
        elif (series[i]>val and not series[i] == np.nan): result [i] = True
        elif (math.isnan(series[i])): result[i] = result[i-1]   
    return result

def greaterequal(series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<val and not series[i] == np.nan): result[i] = False
        elif (series[i]>=val and not series[i] == np.nan): result [i] = True
        elif (math.isnan(series[i])): result[i] = result[i-1]
    return result

def lower (series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<val and not series[i] == np.nan): result[i] = True
        elif (series[i]>=val and not series[i] == np.nan): result [i] = False
        elif (math.isnan(series[i])): result[i] = result[i-1]   
    return result

def lowerequal(series, val):
    result = np.zeros(len(series))
    for i in range(len(series)):
        if (series[i]<=val and not series[i] == np.nan): result[i] = True
        elif (series[i]>val and not series[i] == np.nan): result [i] = False
        elif (math.isnan(series[i])): result[i] = result[i-1] 
    return result
            
def exponential_func(x, a, b, c):
     return a * np.exp(b * x) + c

def evaluate(predictions, original):
    errors = abs(predictions - original)
    max_error = max(errors)
    rerror = np.maximum(np.minimum(np.divide(errors, original),1),-1)
    
    mape = 100 * np.mean(rerror)
    accuracy = 100 - mape
    
    return max_error, accuracy