from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class BaseEvent(BaseModel):
    """
    Universal Base Event class.
    All domain-specific events (e.g., CricketMatch, FootballMatch) must inherit from this.
    """
    id: str = Field(..., description="Unique identifier for the event")
    date: datetime = Field(..., description="Date and time of the event in UTC")
    location: str = Field(..., description="Location of the event (e.g., Stadium, City)")
    latitude: Optional[float] = Field(None, description="Latitude of the location")
    longitude: Optional[float] = Field(None, description="Longitude of the location")
    participants: list[str] = Field(..., description="List of participant IDs or names (e.g., Team A, Team B)")
    
    # Feature Groups
    statistical_features: Dict[str, float] = Field(default_factory=dict, description="Domain specific statistical features")
    astronomical_features: Dict[str, float] = Field(default_factory=dict, description="Universal astronomical features (Vedic/Babylonian)")
    environmental_features: Dict[str, float] = Field(default_factory=dict, description="Universal environmental features (Weather, Geomagnetic)")
    temporal_features: Dict[str, float] = Field(default_factory=dict, description="Time-based features (day of week, month, etc.)")
    
    # Outcome
    outcome: Optional[Any] = Field(None, description="The target variable to predict (e.g., Winner, Score)")

    class Config:
        arbitrary_types_allowed = True

    def get_all_features(self) -> Dict[str, float]:
        """Returns a single flat dictionary of all features."""
        features = {}
        features.update(self.statistical_features)
        features.update(self.astronomical_features)
        features.update(self.environmental_features)
        features.update(self.temporal_features)
        return features
