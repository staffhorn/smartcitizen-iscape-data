import numpy as np
from math import sqrt
import pandas as pd
from src.data.test_utils import combine_data
from dateutil import relativedelta
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.model_selection import cross_val_score
import matplotlib.pyplot as plot
from xgboost import XGBRegressor

def metrics(reference, estimation):
    metrics_dict = dict()
    
    # Average
    avg_ref = np.mean(reference)
    avg_est = np.mean(estimation)
    metrics_dict['avg_ref'] = avg_ref
    metrics_dict['avg_est'] = avg_est

    # Standard deviation
    sigma_ref = np.std(reference)
    sigma_est = np.std(estimation)
    metrics_dict['sig_ref'] = sigma_ref
    metrics_dict['sig_est'] = sigma_est
    
    # Bias
    bias = avg_est-avg_ref
    normalised_bias = float((avg_est-avg_ref)/sigma_ref)
    metrics_dict['bias'] = bias
    metrics_dict['normalised_bias'] = normalised_bias
    
    # Normalized std deviation
    sigma_norm = sigma_est/sigma_ref
    sign_sigma = (sigma_est-sigma_ref)/(abs(sigma_est-sigma_ref))
    metrics_dict['sigma_norm'] = sigma_norm
    metrics_dict['sign_sigma'] = sign_sigma

    # R2
    SS_Residual = sum((estimation-reference)**2)
    SS_Total = sum((reference-np.mean(reference))**2)
    rsquared = max(0, 1 - (float(SS_Residual))/SS_Total)
    metrics_dict['rsquared'] = rsquared

    # RMSD
    RMSD = sqrt((1./len(reference))*SS_Residual)
    RMSD_norm_unb = sqrt(1+np.power(sigma_norm,2)-2*sigma_norm*sqrt(rsquared))
    metrics_dict['RMSD'] = RMSD
    metrics_dict['RMSD_norm_unb'] = RMSD_norm_unb
    
    return metrics_dict

def detect_peak(signal):
    result = np.zeros(signal.shape)
    for i in range(len(signal)-1):
        if signal[i] > signal[i-1]: result[i] = 1
        elif signal[i] < signal[i-1]: result[i] = -1
        elif signal[i] == signal[i-1]: result[i] = 0
    return result

def count_peak(signal, acum = False, sign = True, init = True):
    count_pos = 0
    count_neg = 0
    if init == True: last_peak_sign = 1 
    else: last_peak_sign = -1
    peak = detect_peak(signal)
    result = np.zeros(signal.shape)
    for i in range(len(signal)):
        if acum:
            if peak[i] == 1:
                last_peak_sign = 1
                result[i] = 0
            elif peak[i] == -1:
                last_peak_sign = -1
                result[i] = 0
            elif peak[i] == 0: 
                if i == 0: result[i] = 1
                else: 
                    if sign:
                        result[i] = result[i-1] + last_peak_sign
                    else:
                        result[i] = result[i-1] + 1
        else:
            if peak[i] == 1: 
                count_pos = count_pos + 1
                result[i] = count_pos
            elif peak[i] == -1: 
                count_neg = count_neg + 1
                result[i] = -count_neg
            elif peak[i] == 0: 
                if i == 0: result[i] = 1
                else: result[i] = result[i-1]
    return result

def split_agnostisise(_readings, _reading, _channel):        
    begining_date = '2001-01-01 00:00:00+02:00'
    print (_readings[_reading]['devices'].keys())
    dataframe_combined = combine_data(_readings[_reading]['devices'], False)
    dataframe_combined['change'] = count_peak(dataframe_combined[_channel])

    df = [x for _, x in dataframe_combined.groupby('change')]
    init_date = pd.to_datetime(begining_date).tz_localize('UTC').tz_convert('UTC')
    dataframeAgnostic = pd.DataFrame()
    for i in range(len(df)):
        min_date= pd.to_datetime(df[i].index.min()).tz_convert('UTC')
    
        # print init_date
        # print min_date
        # print relativedelta.relativedelta(min_date, init_date)
        years = relativedelta.relativedelta(min_date, init_date).years
        months = relativedelta.relativedelta(min_date, init_date).months
        days = relativedelta.relativedelta(min_date, init_date).days
        hours = relativedelta.relativedelta(min_date, init_date).hours
        minutes = relativedelta.relativedelta(min_date, init_date).minutes
        seconds = relativedelta.relativedelta(min_date, init_date).seconds
        
        df[i].index =  df[i].index - pd.DateOffset(years = years, months = months, days = days, hours = hours, minutes = minutes, seconds = seconds)
        
        if df[i].loc[:, _channel].mean() > 0.5: prepend = '_ON_' + str(df[i].loc[:,'change'].mean())
        else: prepend = '_OFF_' + str(df[i].loc[:,'change'].mean())
        new_names = list()
        
        for name in df[i].columns:
            # print name
            new_names.append(name + prepend)
        
        df[i].columns = new_names
        dataframeAgnostic = dataframeAgnostic.combine_first(df[i])
    
    return dataframeAgnostic 

def plot_oneshots(readings, channels, device_one_shot):
    for reading in readings:
        devices = readings[reading]['devices'].keys()
        
        # Combine the devices for each reading
        dataframe_combined = combine_data(readings[reading]['devices'], False)
        readings[reading]['devices']['combined'] = dict()
        readings[reading]['devices']['combined']['data'] = dict()
        readings[reading]['devices']['combined']['data'] = dataframe_combined
        
        # Check if the first channel is measuring
        dataframe_combined['measuring'] = 1.0-1.0*np.isnan(readings[reading]['devices']['combined']['data'][channels[0] + '_' + device_one_shot])
        
        # Count the peaks on measuring channel (basicly if it's on) and accumulate how much time has it been measuring
        dataframe_combined['change'] = count_peak(dataframe_combined['measuring'], True)
        
        # Group it be 'change'
        df = [x for _, x in dataframe_combined.groupby('change')]
                
        fig1 = tls.make_subplots(rows=len(channels), cols=1, shared_xaxes=True)
        
        for channel in channels:
            
            indexAB = list() 
            meanAB = list()
            upperAB = list()
            lowerAB = list()
        
            for i in range(len(df)):
                # PM 1.0
                dataframePM = df[i].loc[df[i]['measuring']==1]
                dataA = dataframePM.loc[:,channel + '_' + devices[0]]
                dataB = dataframePM.loc[:,channel + '_' + devices[1]]
                dataAB_y = (dataB - dataA)/dataB
                indexAB.append(i)
                meanAB.append(np.mean(dataAB_y))
                upperAB.append(np.mean(dataAB_y)+np.std(dataAB_y))
                lowerAB.append(np.mean(dataAB_y)-np.std(dataAB_y))
                dataAB_x = i*np.ones(dataAB_y.shape)
                
                fig1.append_trace({'x': dataAB_x, 
                        'y': dataAB_y, 
                        'type': 'scatter', 
                        'name': 'ERROR',
                        'mode': 'markers',
                        'marker': dict(
                            size = 5,
                            color = 'rgba(255, 10, 0, .7)',
                            )}, channels.index(channel)+1 , 1)
                              

                
            fig1.append_trace({'x': indexAB, 
                    'y': meanAB, 
                    'type': 'scatter', 
                    'name': 'Mean', 
                    'mode': 'lines',
                    'marker': dict(
                            color = 'rgba(0, 10, 255, 1)',
                            )}, channels.index(channel)+1 , 1)
            
            fig1.append_trace({'x': indexAB, 
                    'y': upperAB, 
                    'type': 'scatter', 
                    'name': 'Upper Bound',
                    'mode': 'lines',
                    'marker': dict(
                            color = 'rgba(10, 255, 0, .7)',
                            )}, channels.index(channel)+1 , 1)
            
            fig1.append_trace({'x': indexAB, 
                    'y': lowerAB, 
                    'type': 'scatter', 
                    'name': 'Lower Bound',
                    'mode': 'lines',
                    'marker': dict(
                            color = 'rgba(10, 255, 0, .7)',
                            )}, channels.index(channel)+1 , 1)
            
            fig1['layout'].update(height = 1400,
                    showlegend=False,
                    xaxis=dict(title='Measurement Time (s)'),
                    title = reading)
            fig1['layout']['yaxis'+str(channels.index(channel)+1)].update(title=channel + ' Relative Error')

        ply.offline.iplot(fig1)

def minRtarget(targetR):
    return sqrt(1+ np.power(targetR,2)-2*np.power(targetR,2))

def find_closest(A, target):
    #A must be sorted
    idx = A.searchsorted(target)
    idx = np.clip(idx, 1, len(A)-1)
    left = A[idx-1]
    right = A[idx]
    idx -= target - left < right - target
    return idx

def mean_absolute_percentage_error(y_true, y_pred): 
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def timeseries_train_test_split(X, y, test_size):
    """
        Perform train-test split with respect to time series structure
    """
    
    # get the index after which test set starts
    test_index = int(len(X)*(1-test_size))
    
    X_train = X.iloc[:test_index]
    y_train = y.iloc[:test_index]
    X_test = X.iloc[test_index:]
    y_test = y.iloc[test_index:]
    
    return X_train, X_test, y_train, y_test

def plotModelResults(X, y, index, prediction, name, lower, upper, plot_intervals=False, plot_anomalies=False):
    """
        Plots modelled vs fact values, prediction intervals and anomalies
    """

    plot.figure(figsize=(15, 7))
    plot.plot(index, prediction, "g", label="Prediction", linewidth=2.0)
    plot.plot(index, y, alpha = 0.5, label="Actual", linewidth=2.0)
    
    if plot_intervals:
        
        plot.plot(index, lower, "r--", label="Upper bond / Lower bond", alpha=0.5)
        plot.plot(index, upper, "r--", alpha=0.5)
        
    if plot_anomalies:
        anomaly_values = np.array([np.NaN]*len(y))
        anomaly_values[y<lower] = y[y<lower]
        anomaly_values[y>upper] = y[y>upper]
        plot.plot(index, anomaly_values, "o", markersize=5, label = "Anomalies")
    
    error = mean_absolute_percentage_error(prediction, y)
    plot.title(name + ": Mean absolute percentage error {0:.2f}%".format(error))
    plot.legend(loc="best")
    plot.tight_layout()
    plot.grid(True);
    plot.show()

def prepareDataFrame(_data, _frequencyResample, _irrelevantColumns, _numberPasses = 1, _plotModelAnom = True, _scaleAnom = 1.9, _narrowDownFactor = 1, _methodAnom = 'before-after-avg', _append_clean = '_CLEAN'):
    '''
        Function for Dataframe preparation: resampling and anomalies cleaning
        data: Pandas dataframe with datetime index
        frequency: target datetime index frequency to resample to
        irrelevant_columns: ignore columns for anomaly detection (tipically BATT, BATT_CHG_RATE and LIGHT)
        plotModelAnom: plot anomaly model
        scaleAnom: range for anomaly detection thresholds (between 1 and 3)
        narrow_down_factor: a tighter factor each time
        methodAnom = anomaly treatment method
    '''

    def prepareForAnomalies(series_prepare, lag_start, lag_end, test_size):
        """
            series: pd.DataFrame
                dataframe with timeseries
            lag_start: int
                initial step back in time to slice target variable 
                example - lag_start = 1 means that the model 
                          will see yesterday's values to predict today
            lag_end: int
                final step back in time to slice target variable
                example - lag_end = 4 means that the model 
                          will see up to 4 days back in time to predict today
            test_size: float
                size of the test dataset after train/test split as percentage of dataset
            target_encoding: boolean
                if True - add target averages to the dataset
            
        """
        
        # copy of the initial dataset
        data_prepare = pd.DataFrame(series_prepare.copy())
        data_prepare.columns = ["y"]
        
        # lags of series
        for i in range(lag_start, lag_end):
            data_prepare["lag_{}".format(i)] = data_prepare.y.shift(i)
        
        # # train-test split
        data_prepare = data_prepare.fillna(method='bfill').fillna(method='ffill')

        y = data_prepare.y
        X = data_prepare.drop(['y'], axis=1)

        index = data_prepare.index
        X_train, X_test, y_train, y_test =\
            timeseries_train_test_split(X, y, test_size=test_size)
        return X_train, X_test, y_train, y_test, index

    def calculateAnomalies(data_calculate, frecuency_calculate = '1Min' , scale_calculate = 2, plot_model_calculate = False):
        print ('Scale factor:', scale_calculate)

        name_calculate = data_calculate.name
        scaler = StandardScaler()
        tscv = TimeSeriesSplit(n_splits=5)
        
        # Extract frequency and convert it to lags
        offset = pd.tseries.frequencies.to_offset(frecuency_calculate)
        alias = pd.tseries.frequencies.get_base_alias(frecuency_calculate)
        
        LUT_CONVERT_FREQ = (['Min', 1], 
                       ['S', 1/60], 
                       ['H', 60])
        
        factor = 0
        for item_lut in LUT_CONVERT_FREQ:
            if item_lut[0] == alias:
                factor = item_lut[1]*offset.n
        
        # good lag for 1Min frequency seems to be 60 for all signals
        lag_end = int(max(10, 60/factor))
        
        X_calculate, _, y_calculate, _, index_calculate =\
            prepareForAnomalies(data_calculate, lag_start=3, lag_end = lag_end, 
                test_size=0)

        anomalies_calculate = np.zeros(len(y_calculate))
        
        if (len(y_calculate)):
            print ('\tCalculating...', name_calculate)

            X_scaled_calculate = scaler.fit_transform(X_calculate)
             
            xgb = XGBRegressor()
            model_calculate = xgb.fit(X_scaled_calculate, y_calculate)
            
            prediction_calculate = model_calculate.predict(X_scaled_calculate)
            
            cv = cross_val_score(model_calculate, X_scaled_calculate, y_calculate,
                                cv = tscv, 
                                scoring = "neg_mean_squared_error")
            
            deviation_calculate = np.sqrt(cv.std())
            
            lower_calculate = prediction_calculate - (scale_calculate * deviation_calculate)
            upper_calculate = prediction_calculate + (scale_calculate * deviation_calculate)
                    
            anomalies_calculate [y_calculate < lower_calculate] = 1
            anomalies_calculate [y_calculate > upper_calculate] = 1
            
            if plot_model_calculate: 
                plotModelResults(X_calculate, y_calculate, index_calculate, 
                                prediction_calculate, name_calculate,
                                lower_calculate, upper_calculate, 
                                True, True)
                
        anomalies_calculate = pd.Series(anomalies_calculate)
        anomalies_calculate.index = index_calculate
        
        return anomalies_calculate
    
    def cleanAnomalies(values_array, anomalies_array, method):
        '''
            Function to clean dataframe, provided a column with anomalies and a marker
            column, with ones where the anomalies are found.
            Method can be selected among:
                - before-after-avg: averages the prior and posterior element of the anomaly
                - fill-...:
                    - zeroes: inputs a 0 in the anomaly
                    - nan: inputs a nan in the anomaly
                    - avg: 
        '''

        list_anom = list(np.where(anomalies_array == 1)[0])
        values_array_clean = values_array.copy()
        
        if method == 'before-after-avg':
            for item_anomaly in list_anom:
                if item_anomaly < len(values_array_clean)-2:

                    values_array_clean[item_anomaly] = (values_array_clean[item_anomaly - 1]\
                                + values_array_clean[item_anomaly + 1])/2


        elif method == 'fill-zeroes':
            for item_anomaly in list_anom:
                values_array_clean[item_anomaly] = 0
        elif method == 'fill-nan':
            for item_anomaly in list_anom:
                values_array_clean[item_anomaly] = np.nan
        elif method == 'fill-avg':
            average = np.mean(values_array_clean)
            for item_anomaly in list_anom:
                values_array_clean[item_anomaly] = average 
        elif method == 'fill-median':
            median = np.median(values_array_clean)
            for item_anomaly in list_anom:
                values_array_clean[item_anomaly] = median    
        
        return values_array_clean

    append_anomalies = '_ANOM'

    dataFrame = _data.copy()
    dataFrame.resample(_frequencyResample).bfill()

    ## Calculate anomalies for each column and treat them
    for column in dataFrame.columns:
        if append_anomalies not in column:
            if column not in _irrelevantColumns:

                values_array = dataFrame[column]

                for pass_number in range(_numberPasses):
                
                    print ('Calculating: ' + column + '. Pass#: ' + str(pass_number))

                    anomalies_array = calculateAnomalies(values_array,
                                                        _frequencyResample, 
                                                        scale_calculate = _scaleAnom/(np.power(_narrowDownFactor, pass_number)), 
                                                        plot_model_calculate = _plotModelAnom)

                    dataFrame[column + '_ANOM_PASS_' + str(pass_number)] = anomalies_array

                    print ('Cleaning: ' + column + '. Pass#: ' + str(pass_number) + '. Method:' + _methodAnom)

                    clean_array = cleanAnomalies(values_array, anomalies_array,
                                                method = _methodAnom)

                    values_array = clean_array

                print (column, 'has been cleaned')
                dataFrame[column + _append_clean] = clean_array.values

                plot.figure(figsize=(15, 7))
                plot.plot(dataFrame.index, dataFrame[column + _append_clean], "g", label="Final Signal", linewidth=2.0)
                plot.title('Final clean signal for {}, after {} passes'.format(column, _numberPasses))
                plot.legend(loc="best")
                plot.tight_layout()
                plot.grid(True);
                plot.show()

            else:
                print ('Ignoring', column)
        print ('-------')
        
    return dataFrame