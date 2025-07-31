from sqlalchemy.orm import sessionmaker, scoped_session
from database.models import get_engine

# Create a session factory
engine = get_engine()
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def get_session():
    """Get a database session"""
    return Session()

def close_session(session):
    """Close a database session"""
    session.close() 