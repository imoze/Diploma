import librosa
import numpy as np

def KrumanslKey(chroma_vector):
    
    major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 
                     2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
    
    minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                     2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
    
    major_profile = np.array(major_profile) / np.sum(major_profile)
    minor_profile = np.array(minor_profile) / np.sum(minor_profile)
    
    best_key = None
    best_mode = None
    best_correlation = -1
    
    for tonic in range(12):
        shifted_chroma = np.roll(chroma_vector, -tonic)
        
        corr_major = np.corrcoef(shifted_chroma, major_profile)[0, 1]
        
        corr_minor = np.corrcoef(shifted_chroma, minor_profile)[0, 1]
        
        if corr_major > best_correlation:
            best_correlation = corr_major
            best_key = tonic
            best_mode = 'major'
            
        if corr_minor > best_correlation:
            best_correlation = corr_minor
            best_key = tonic
            best_mode = 'minor'
    
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    key_name = notes[best_key]
    
    return key_name, best_mode, best_correlation

def KeyMode(y, sr):
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)
    chroma_weighted = chroma * rms
    chroma_mean = np.sum(chroma_weighted, axis=1) / np.sum(rms)
    key, mode, conf = KrumanslKey(chroma_mean)
    return key, mode

'''
y, sr = librosa.load("C:\\0.0.Diploma\\AudioAnalysis\\ACDC_-_Back_In_Black_47830042.mp3")
chroma = librosa.feature.chroma_stft(y=y, sr=sr)
chroma_mean = np.mean(chroma, axis=1)
key, mode, confidence = KrumanslKey(chroma_mean)
print(f"Тональность: {key} {mode}")
print(f"Уверенность: {confidence:.3f}")
'''