"""
Database models for the Research Paper Summarization System.
"""

import uuid
from typing import Generator
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
import sqlalchemy as sa

from ..config.settings import settings

# Database availability check
try:
    from sqlalchemy import create_engine
    DATABASE_AVAILABLE = True
except ImportError:
    print("Warning: SQLAlchemy not installed. Database features disabled.")
    DATABASE_AVAILABLE = False

if DATABASE_AVAILABLE:
    Base = declarative_base()
    
    class PaperModel(Base):
        """Database model for research papers"""
        __tablename__ = "papers"
        
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        title = Column(Text, nullable=False)
        authors = Column(JSON)  # Store as JSON array
        abstract = Column(Text)
        content = Column(Text)
        doi = Column(String, unique=True)
        url = Column(String)
        file_path = Column(String)
        topics = Column(JSON)  # Store as JSON array
        created_at = Column(DateTime, default=sa.func.now())
    
    class WorkflowModel(Base):
        """Database model for workflow tracking"""
        __tablename__ = "workflows"
        
        id = Column(String, primary_key=True)
        status = Column(String, default="pending")
        progress = Column(Float, default=0.0)
        message = Column(String)
        input_params = Column(JSON)
        results = Column(JSON)
        created_at = Column(DateTime, default=sa.func.now())
    
    # Initialize database
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    def get_db() -> Generator:
        """Get database session"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    def init_database():
        """Initialize database tables"""
        Base.metadata.create_all(bind=engine)
        
else:
    Base = None
    PaperModel = None
    WorkflowModel = None
    engine = None
    SessionLocal = None
    
    def get_db():
        """Fallback when database is not available"""
        return None
    
    def init_database():
        """Fallback when database is not available"""
        pass
