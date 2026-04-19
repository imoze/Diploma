import numpy as np
from scipy import stats

def ExtractStaticCharacteristics(time_series : np.ndarray):
    time_series = time_series[~np.isnan(time_series)]
    p0, p5, q25, q50, q75, p95, p100 = np.percentile(time_series, [0, 5, 25, 50, 75, 95, 100])
    std = np.std(time_series)
    mean = np.mean(time_series)
    static_characteristics = {
        'mean':mean,
        'median':q50,
        'variance':np.var(time_series),
        'std_dev':std,
        'range':p100-p0,
        'IQR':q75-q25,
        'q25':q25,
        'q75':q75,
        'MAD':np.mean(np.abs(time_series - mean)),
        'min':p0,
        'max':p100,
        'p5':p5,
        'p95':p95,
        'skewness':stats.skew(time_series),
        'kurtosis':stats.kurtosis(time_series),
        'CoV':std/np.abs(mean)
    }
    return static_characteristics