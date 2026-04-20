import joblib

from AudioAnalysis.AudioFeatures import ExtractAudioFeatures
from AudioAnalysis.ConvertToVector import ConvertToVector

def AnalyseTrack(scaler, pca, track_fp):
    return pca.transform(scaler.transform([ConvertToVector(ExtractAudioFeatures(track_fp))]))

'''scaler_loaded = joblib.load('C:\\0.0.Diploma\\backend\\models\\scaler.pkl')
pca_loaded = joblib.load('C:\\0.0.Diploma\\backend\\models\\pca.pkl')
res = AnalyseTrack(scaler_loaded, pca_loaded, 'C:\\0.0.Diploma\\Tracks\\Rock\\Red_Hot_Chili_Peppers\\The_Studio_Album_Collection_1991-2011\\1.mp3')
print(res)
print(res.shape)'''