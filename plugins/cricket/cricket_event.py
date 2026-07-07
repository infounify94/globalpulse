from typing import Optional
from pydantic import Field
from core.models.base_event import BaseEvent

class CricketEvent(BaseEvent):
    """
    Cricket specific event representation.
    Inherits all universal properties from BaseEvent (date, location, participants)
    and adds domain-specific metadata.
    """
    
    match_type: str = Field(..., description="e.g., T20, ODI, Test")
    venue_name: str = Field(..., description="Name of the stadium")
    
    # Participants are typically team_a and team_b, let's map them explicitly
    # Note: participants list from BaseEvent will still be populated [team_a, team_b]
    team_a: str = Field(..., description="First team")
    team_b: str = Field(..., description="Second team")
    
    toss_winner: Optional[str] = Field(None, description="Team that won the toss")
    toss_decision: Optional[str] = Field(None, description="bat or field")
