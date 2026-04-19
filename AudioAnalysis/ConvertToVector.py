import numpy as np

from AudioAnalysis.AudioFeatures import ExtractAudioFeatures

notes_converting = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
stats = ['mean','median','variance','std_dev','range','IQR','q25','q75','MAD','min','max','p5','p95','skewness','kurtosis','CoV']

def ConvertToVector(AudioFeatures: dict):
    res = list()

    for element in AudioFeatures['MFCC']:
        for stat in stats:
            res.append(element[stat])

    for element in AudioFeatures['spectral_contrast']:
        for stat in stats:
            res.append(element[stat])

    for stat in stats:
            res.append(AudioFeatures['spectral_centroid'][stat])

    for stat in stats:
            res.append(AudioFeatures['spectral_bandwith'][stat])

    for stat in stats:
            res.append(AudioFeatures['spectral_rolloff'][stat])

    for element in AudioFeatures['chromagramm']:
        for stat in stats:
            res.append(element[stat])

    for stat in stats:
            res.append(AudioFeatures['loudness'][stat])

    for stat in stats:
            res.append(AudioFeatures['ZCR'][stat])

    res.append(AudioFeatures['BPM'])
    res.append(notes_converting[AudioFeatures['key']])
    res.append(1 if AudioFeatures['mode'] == 'major' else 0)

    return np.array(res, dtype=np.float64)

#print(ConvertToVector(ExtractAudioFeatures('C:\\0.0.Diploma\\Tracks\\ACDC_-_Back_In_Black_47830042.mp3')))