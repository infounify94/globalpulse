from typing import List, Any
from core.memory.schema import DBEvent, DBCricketMatchMetadata, DBFeatureStatistics, DBFeatureAstronomy
from plugins.cricket.cricket_event import CricketEvent
from core.generators.astronomy_generator import AstronomyGenerator
from plugins.cricket.cricket_stats_generator import CricketStatsGenerator

class FeaturePipeline:
    """
    Transforms raw DB models into Python Domain Models, passes them through generators,
    and returns DB Feature models ready for insertion.
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.astro_gen = AstronomyGenerator()
        self.stats_gen = CricketStatsGenerator(engine)

    def run(self, db_event: DBEvent, db_metadata: DBCricketMatchMetadata) -> List[Any]:
        """
        Runs all configured feature generators for the given event.
        """
        # Construct the Domain Model required by generators
        domain_event = CricketEvent(
            id=db_event.id,
            date=db_event.date,
            location=db_event.venue_id or "unknown",
            participants=[db_metadata.team_a_id, db_metadata.team_b_id],
            match_type=db_metadata.match_type,
            venue_name=db_event.venue_id or "unknown",
            team_a=db_metadata.team_a_id,
            team_b=db_metadata.team_b_id,
            toss_winner=db_metadata.toss_winner_id,
            toss_decision=db_metadata.toss_decision
        )
        
        db_features = []
        
        # 1. Generate Astronomical Features
        try:
            astro_features = self.astro_gen.generate(domain_event)
            if astro_features:
                db_features.append(DBFeatureAstronomy(
                    event_id=db_event.id,
                    features=astro_features
                ))
        except Exception as e:
            import logging
            logging.error(f"Failed to generate astronomy features for {db_event.id}: {e}")
            
        # 2. Generate Statistical Features
        try:
            stat_features = self.stats_gen.generate(domain_event)
            if stat_features:
                db_features.append(DBFeatureStatistics(
                    event_id=db_event.id,
                    features=stat_features
                ))
        except Exception as e:
            import logging
            logging.error(f"Failed to generate statistical features for {db_event.id}: {e}")
            
        return db_features
