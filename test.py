from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DB.models import Track

DATABASE_URL = "postgresql://db_user:diploma@localhost/DiplomaDB"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

tr = Track()
tr.id = '3f8a9c2e-7b4d-4f1a-9d2c-5e6b8a1f0c9d',
tr.name = 'test',
tr.release_date = ''
session.add(tr)