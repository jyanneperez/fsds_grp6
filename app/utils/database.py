from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

# Get full DATABASE_URL from environment (Render provides this)
DATABASE_URL = os.getenv("DATABASE_URL")

# Set up the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# SessionLocal to manage database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()