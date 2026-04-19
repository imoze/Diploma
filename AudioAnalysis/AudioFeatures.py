import librosa
import numpy as np

from AudioAnalysis.KrumhanslSmukler import KeyMode
from AudioAnalysis.StaticCharacteristics import ExtractStaticCharacteristics

def ExtractAudioFeatures(track_fp):
    y, sr = librosa.load(track_fp)
    #y - track, sr - sample rate

    key, mode = KeyMode(y=y, sr=sr)
    track_params = {
        'MFCC'              : librosa.feature.mfcc(y=y, sr=sr),
        'spectral_contrast' : librosa.feature.spectral_contrast(y=y, sr=sr),
        'spectral_centroid' : librosa.feature.spectral_centroid(y=y, sr=sr),
        'spectral_bandwith' : librosa.feature.spectral_bandwidth(y=y, sr=sr),
        'spectral_rolloff'  : librosa.feature.spectral_rolloff(y=y, sr=sr),
        'chromagramm'       : librosa.feature.chroma_stft(y=y, sr=sr),
        'loudness'          : librosa.feature.rms(y=y),
        'ZCR'               : librosa.feature.zero_crossing_rate(y=y),
        'BPM'               : librosa.feature.tempo(y=y, sr=sr)[0],
        'key'               : key,
        'mode'              : mode
    }


    l = len(track_params)
    count = 0
    for i in track_params.keys():
        if isinstance(track_params[i], np.ndarray):
            n = track_params[i].shape
            if n[0] > 1:
                res = list()
                for j in range(n[0]):
                    res.append(ExtractStaticCharacteristics(track_params[i][j]))
                track_params[i] = res
            else:
                track_params[i] = ExtractStaticCharacteristics(track_params[i])
        else:
            pass
        count += 1

    return track_params

    '''for i in track_params.keys():
        if isinstance(track_params[i], list):
            print(i)
            for j in range(len(track_params[i])):
                print(j+1)
                for k in track_params[i][j].keys():
                    print(f'    {k}:{track_params[i][j][k]}')
            print()
        elif isinstance(track_params[i], dict):
            print(i)
            for j in track_params[i].keys():
                print(f'    {j}:{track_params[i][j]}')
            print()
        else:
            print(i, track_params[i], '\n')'''