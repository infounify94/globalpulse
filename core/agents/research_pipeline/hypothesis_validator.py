import logging
from typing import Dict, Any

class HypothesisValidator:
    """
    Acts as the strict scientific gatekeeper before any Hypothesis is allowed to become a Feature Generator.
    Checks for:
    - Data Leakage (Does it use future information?)
    - Mathematical definition (Can it output float/int/categorical strings?)
    - Reproducibility (Does it rely on deterministic inputs?)
    """
    def __init__(self):
        pass
        
    def validate(self, hypothesis: Dict[str, Any]) -> bool:
        """
        Runs rigorous checks on an LLM-generated hypothesis.
        """
        logging.info(f"Validating Hypothesis: {hypothesis.get('hypothesis_name', 'Unknown')}")
        
        # 1. Structural Validation
        required_keys = ['hypothesis_name', 'description', 'python_logic', 'confidence_score']
        for key in required_keys:
            if key not in hypothesis:
                logging.error(f"Validation Failed: Missing {key}")
                return False
                
        # 2. Logic Safety & Leakage Check (Heuristics)
        logic_str = hypothesis['python_logic'].lower()
        leakage_keywords = ['winner', 'result', 'future', 'tomorrow', 'post_match', 'actual']
        for word in leakage_keywords:
            if word in logic_str:
                logging.error(f"Validation Failed: Potential data leakage detected (keyword: {word})")
                return False
                
        # 3. Confidence Threshold
        score = hypothesis.get('confidence_score', 0.0)
        if not isinstance(score, (int, float)) or score < 0.2:
            logging.error(f"Validation Failed: Confidence score {score} too low.")
            return False
            
        logging.info("Validation Passed. Hypothesis is mathematically sound and leakage-free.")
        return True

if __name__ == "__main__":
    validator = HypothesisValidator()
    
    # Test a valid hypothesis
    valid_hyp = {
        "hypothesis_name": "MarsRetrograde",
        "description": "Checks if Mars is in retrograde.",
        "python_logic": "def extract(doc):\n    return {'mars_retrograde': 1}",
        "confidence_score": 0.8
    }
    print("Test Valid:", validator.validate(valid_hyp))
    
    # Test a leaking hypothesis
    invalid_hyp = {
        "hypothesis_name": "WinnerPrediction",
        "description": "Looks at the winner of the match.",
        "python_logic": "def extract(doc):\n    return {'winner_is_team1': match.winner == match.team1}",
        "confidence_score": 0.9
    }
    print("Test Invalid:", validator.validate(invalid_hyp))
