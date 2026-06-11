from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./cv_analysis.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class CVResult(Base):
    __tablename__ = "cv_results"

    id                  = Column(Integer, primary_key=True, index=True)
    filename            = Column(String)
    original_filename   = Column(String)          # original name the user uploaded
    ats_score           = Column(Float)
    match_score         = Column(Float)
    semantic_score      = Column(Float)
    created_at          = Column(DateTime, default=datetime.now)

    # Detail fields (JSON-serialized lists/strings)
    summary             = Column(Text, default="")
    ats_explanation     = Column(Text, default="")
    found_skills        = Column(Text, default="")   # comma-separated
    missing_skills      = Column(Text, default="")
    recommended_roles   = Column(Text, default="")   # JSON
    matched_job_skills  = Column(Text, default="")
    missing_job_skills  = Column(Text, default="")
    recommendations     = Column(Text, default="")   # JSON array
    job_description     = Column(Text, default="")
    required_skills     = Column(Text, default="")   # comma-separated


Base.metadata.create_all(bind=engine)