import json
import numpy as np

import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from AudioAnalysis.AudioFeatures import ExtractAudioFeatures
from AudioAnalysis.ConvertToVector import ConvertToVector

def TrainScalerPCA(tracks='C:\\0.0.Diploma\\Tracks\\tracks.json'):
    with open(tracks, 'r') as file:
        track_list = json.load(file)

    feature_vectors = list()
    l = len(track_list)

    index = 0
    with open('C:\\0.0.Diploma\\Tracks\\tmp.json', "r", encoding="utf-8") as f:
        for line in f:
            index = int(line[1:line.find(' ')-1:])
            v = line[line.find(' ')+2:-3:].split(', ')
            feature_vectors.append(np.array(v))

    with open('C:\\0.0.Diploma\\Tracks\\tmp.json', "a", encoding="utf-8") as f:

        for i, track_fp in enumerate(track_list):
            if i < index:
                print(f'Already analysed ({i+1})')
                continue
            print(f'Analysing track {i+1}')
            features = ExtractAudioFeatures(track_fp)
            vector = ConvertToVector(features)
            feature_vectors.append(vector)
            json.dump([i+1, vector.tolist()], f, ensure_ascii=False)
            f.write('\n')
            f.flush()

            print(f'Analys complete\n{abs(i+1-l)} remaining\n\n')

    feature_matrix = np.array(feature_vectors)
    #print(feature_matrix.shape)


    scaler = StandardScaler()
    scaled_feature_matrix = scaler.fit_transform(feature_matrix)

    pca = PCA(n_components=0.95)
    transformed_feature_matrix = pca.fit_transform(scaled_feature_matrix)
    n = transformed_feature_matrix.shape[1]

    joblib.dump(scaler, 'Models/scaler.pkl')
    joblib.dump(pca, 'Models/pca.pkl')
    with open("Models/model_metadata.json", "w") as f:
        json.dump({
            'version':1,
            'n_dimensions':n
        }, f)

    '''
    scaler_loaded = joblib.load('Models/scaler.pkl')
    pca_loaded = joblib.load('Models/pca.pkl')
    test_matrix = pca_loaded.transform(scaler_loaded.transform(feature_matrix))
    print('OK!' if np.allclose(test_matrix, transformed_feature_matrix) else 'FAIL!')
    '''


#TrainScalerPCA()
'''
scaler_loaded = joblib.load('C:\\0.0.Diploma\\backend\\models\\scaler.pkl')
pca_loaded = joblib.load('C:\\0.0.Diploma\\backend\\models\\pca.pkl')
test_vector1 = pca_loaded.transform(scaler_loaded.transform([ConvertToVector(ExtractAudioFeatures('C:\\0.0.Diploma\\Tracks\\Rock\\Red_Hot_Chili_Peppers\\The_Studio_Album_Collection_1991-2011\\1.mp3'))]))
test_vector2 = pca_loaded.transform(scaler_loaded.transform([ConvertToVector(ExtractAudioFeatures('C:\\0.0.Diploma\\Tracks\\Rock\\Red_Hot_Chili_Peppers\\The_Studio_Album_Collection_1991-2011\\1.mp3'))]))
print('OK!' if test_vector1.shape[1] == test_vector2.shape[1] else 'FAIL!')
'''