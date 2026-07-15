import abc
from typing import Dict, Any

class FeatureGenerator(abc.ABC):
    """
    Takes a mathematical formulation of a hypothesis and a historical match date,
    and computes the feature strictly using knowledge available BEFORE the match date.
    """
    
    @abc.abstractmethod
    def compute_features(self, match_metadata: Dict[str, Any], match_date: str) -> Dict[str, float]:
        """
        Compute features for a specific match given the date.
        Must strictly avoid data leakage.
        """
        pass
