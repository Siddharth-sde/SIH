from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Uses a local SQLite database file named material_master.db
DATABASE_URL = "sqlite:///./material_master.db"

# connect_args is needed only for SQLite to allow multiple threads
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()