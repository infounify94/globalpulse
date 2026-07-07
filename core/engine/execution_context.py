import os
from enum import Enum
import logging

class ExecutionMode(Enum):
    RESEARCH = "research"
    PRODUCTION = "production"

class GlobalPulseContext:
    """
    Manages the global execution state of the engine.
    Research Mode: Enables Optuna, extensive feature exploration, allows experimental code.
    Production Mode: Locks down hyperparameter tuning, uses ONLY the Champion model, enforces strict performance limits.
    """
    
    def __init__(self):
        # Default to production for safety unless explicitly overridden
        mode_str = os.environ.get("GLOBALPULSE_MODE", "production").lower()
        self.mode = ExecutionMode.RESEARCH if mode_str == "research" else ExecutionMode.PRODUCTION
        logging.info(f"GlobalPulse Context initialized in {self.mode.name} mode.")
        
    def is_research(self) -> bool:
        return self.mode == ExecutionMode.RESEARCH
        
    def is_production(self) -> bool:
        return self.mode == ExecutionMode.PRODUCTION
        
    def enforce_production_safeguards(self):
        """Raises an exception if an experimental feature is called in Production."""
        if self.is_production():
            raise PermissionError("Action prohibited in PRODUCTION mode. Switch to RESEARCH mode to execute.")

# Singleton context
context = GlobalPulseContext()
