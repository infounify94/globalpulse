import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# pgvector is only available with PostgreSQL. Fall back gracefully for SQLite (local dev).
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    # Create a stub so schema.py doesn't crash in SQLite environments
    class Vector:
        def __class_getitem__(cls, item):
            return String  # Store as string in SQLite (not queryable, but won't crash)
        def __call__(self, *args, **kwargs):
            return String()

Base = declarative_base()


class DBTeam(Base):
    __tablename__ = 'teams'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    domain = Column(String, nullable=False, default="cricket")

class DBPlayer(Base):
    __tablename__ = 'players'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=False, default="cricket")

class DBVenue(Base):
    __tablename__ = 'venues'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

class DBEvent(Base):
    __tablename__ = 'events'
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True) # e.g., cricket
    date = Column(DateTime, nullable=False, index=True) # Crucial for Walk-Forward Validation
    venue_id = Column(String, ForeignKey('venues.id'), nullable=True)
    outcome = Column(String, nullable=True) # e.g., "team_a_won", "draw"
    
    venue = relationship("DBVenue")
    metadata_cricket = relationship("DBCricketMatchMetadata", back_populates="event", uselist=False)
    statistics = relationship("DBFeatureStatistics", back_populates="event", uselist=False)
    astronomy = relationship("DBFeatureAstronomy", back_populates="event", uselist=False)
    environment = relationship("DBFeatureEnvironment", back_populates="event", uselist=False)
    vector = relationship("DBFeatureVector", back_populates="event", uselist=False)

class DBCricketMatchMetadata(Base):
    __tablename__ = 'cricket_match_metadata'
    event_id = Column(String, ForeignKey('events.id'), primary_key=True)
    match_type = Column(String, nullable=False)
    toss_winner_id = Column(String, ForeignKey('teams.id'), nullable=True)
    toss_decision = Column(String, nullable=True) # "bat" or "field"
    team_a_id = Column(String, ForeignKey('teams.id'), nullable=False)
    team_b_id = Column(String, ForeignKey('teams.id'), nullable=False)
    
    event = relationship("DBEvent", back_populates="metadata_cricket")

class DBInning(Base):
    __tablename__ = 'innings'
    id = Column(String, primary_key=True)
    event_id = Column(String, ForeignKey('events.id'), nullable=False, index=True)
    inning_number = Column(Integer, nullable=False)
    batting_team_id = Column(String, ForeignKey('teams.id'), nullable=False)
    bowling_team_id = Column(String, ForeignKey('teams.id'), nullable=False)
    total_runs = Column(Integer, default=0)
    total_wickets = Column(Integer, default=0)
    
    event = relationship("DBEvent")

class DBDelivery(Base):
    """Note: Might be massive in size. Partitioning by year is recommended at the DB level."""
    __tablename__ = 'deliveries'
    id = Column(String, primary_key=True) # e.g., inning_id_over_ball
    inning_id = Column(String, ForeignKey('innings.id'), nullable=False, index=True)
    over_number = Column(Integer, nullable=False)
    ball_number = Column(Integer, nullable=False)
    batter_id = Column(String, ForeignKey('players.id'), nullable=False)
    bowler_id = Column(String, ForeignKey('players.id'), nullable=False)
    runs_batter = Column(Integer, default=0)
    runs_extras = Column(Integer, default=0)
    is_wicket = Column(Boolean, default=False)
    wicket_type = Column(String, nullable=True)

class DBFeatureStatistics(Base):
    __tablename__ = 'features_statistics'
    event_id = Column(String, ForeignKey('events.id'), primary_key=True)
    # Storing features as JSONB allows for dynamic addition of new stats without schema changes
    features = Column(JSON, nullable=False, default={})
    
    event = relationship("DBEvent", back_populates="statistics")

class DBFeatureAstronomy(Base):
    __tablename__ = 'features_astronomy'
    event_id = Column(String, ForeignKey('events.id'), primary_key=True)
    features = Column(JSON, nullable=False, default={})
    
    event = relationship("DBEvent", back_populates="astronomy")

class DBFeatureEnvironment(Base):
    __tablename__ = 'features_environment'
    event_id = Column(String, ForeignKey('events.id'), primary_key=True)
    features = Column(JSON, nullable=False, default={})
    
    event = relationship("DBEvent", back_populates="environment")

class DBFeatureVector(Base):
    __tablename__ = 'feature_vectors'
    event_id = Column(String, ForeignKey('events.id'), primary_key=True)
    # In PostgreSQL with pgvector, this stores a real 1536-dim embedding.
    # In SQLite (dev), this stores as a JSON string (not queryable for similarity).
    embedding = Column(String if not HAS_PGVECTOR else Vector(1536))

    event = relationship("DBEvent", back_populates="vector")


class DBFeatureRegistry(Base):
    """Stores metadata and importance scores for all generated features."""
    __tablename__ = 'feature_registry'
    id = Column(String, primary_key=True) # e.g. "cricket_stat_team_a_win_pct_5"
    feature_name = Column(String, nullable=False, unique=True)
    domain = Column(String, nullable=False) # e.g. "cricket", "universal"
    description = Column(String, nullable=True)
    baseline_importance = Column(Float, default=0.0)
    correlation_score = Column(Float, default=0.0)
    usefulness_flag = Column(Boolean, default=True)

class DBExperimentRegistry(Base):
    """Tracks every Walk-Forward run to guarantee reproducibility."""
    __tablename__ = 'experiment_registry'
    id = Column(String, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    dataset_version = Column(String, nullable=False)
    feature_version = Column(String, nullable=False)
    feature_families_tested = Column(String, nullable=False) # JSON list
    winning_model_id = Column(String, nullable=True)
    metrics_summary = Column(JSON, nullable=True)
    
class DBModelRegistry(Base):
    """Permanent storage for every trained model."""
    __tablename__ = 'model_registry'
    id = Column(String, primary_key=True)
    experiment_id = Column(String, ForeignKey('experiment_registry.id'))
    algorithm = Column(String, nullable=False)
    train_start_year = Column(Integer, nullable=False)
    train_end_year = Column(Integer, nullable=False)
    test_start_year = Column(Integer, nullable=False)
    test_end_year = Column(Integer, nullable=False)
    parameters = Column(JSON, nullable=False)
    random_seed = Column(Integer, nullable=False)
    performance_metrics = Column(JSON, nullable=False)
    calibration_metrics = Column(JSON, nullable=False)
    execution_time_seconds = Column(Float, nullable=False)
    model_artifact_path = Column(String, nullable=True)  # Path to .joblib file on disk
    is_champion = Column(Boolean, default=False)  # Is this the current production model?

class DBPredictionStore(Base):
    """Stores every prediction generated during Walk-Forward validation."""
    __tablename__ = 'prediction_store'
    id = Column(String, primary_key=True)
    match_id = Column(String, ForeignKey('events.id'))
    model_id = Column(String, ForeignKey('model_registry.id'))
    prediction_timestamp = Column(DateTime, nullable=False)
    predicted_winner_id = Column(String, nullable=False)
    probability = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True) # Calibrated confidence
    dataset_version = Column(String, nullable=True) # Enforces dataset traceability
    feature_version = Column(String, nullable=True) # Enforces feature traceability
    actual_winner_id = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    top_driving_features = Column(JSON, nullable=True) # SHAP top 3

class DBPredictionLineage(Base):
    """Full audit trail for every prediction. Answers: which model, data, code produced this?"""
    __tablename__ = 'prediction_lineage'
    id = Column(String, primary_key=True)
    prediction_id = Column(String, ForeignKey('prediction_store.id'), nullable=False)
    model_id = Column(String, ForeignKey('model_registry.id'), nullable=False)
    model_artifact_path = Column(String, nullable=True)   # Exact .joblib path
    dataset_version = Column(String, nullable=True)        # e.g. 'v7'
    feature_version = Column(String, nullable=True)        # e.g. 'v3'
    hyperparameters = Column(JSON, nullable=True)          # Exact params used
    feature_families_used = Column(String, nullable=True)  # JSON list
    connector_name = Column(String, nullable=True)         # Which API supplied data
    connector_version = Column(String, nullable=True)      # API version
    git_commit_hash = Column(String, nullable=True)        # Code version
    training_timestamp = Column(DateTime, nullable=True)   # When model was trained
    prediction_timestamp = Column(DateTime, nullable=False)

# Database setup helper
def get_engine(db_url: str = None):
    if not db_url:
        db_url = os.environ.get("GLOBALPULSE_DB_URL", "postgresql://user:password@localhost:5432/globalpulse")
    return create_engine(db_url)

def create_tables(engine):
    Base.metadata.create_all(engine)
