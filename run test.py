'''from uuid6 import uuid7
from datetime import date
from app.db.models import Track
from app.db.session import get_db

db = next(get_db())

track = Track(
    id=uuid7(),
    name="Test Track",
    release_date=date.today(),
    duration=180,
    parts_plays=[0 for i in range(100)],
    feature_vector=[0 for i in range(150)],
    track_path='test path'
)

db.add(track)
db.commit()
db.refresh(track)'''


import joblib
from AudioAnalysis.NewTrackAnalysis import AnalyseTrack
scaler_loaded = joblib.load('C:\\0.0.Diploma\\models\\scaler.pkl')
pca_loaded = joblib.load('C:\\0.0.Diploma\\models\\pca.pkl')
res = AnalyseTrack(scaler_loaded, pca_loaded, 'C:\\0.0.Diploma\\Tracks\\Rock\\Red_Hot_Chili_Peppers\\The_Studio_Album_Collection_1991-2011\\1.mp3')
print(res)
print(res.shape)