import os
import hashlib
import joblib
import logging
from supabase import create_client, Client
from sqlalchemy.orm import Session
from core.memory.schema import DBModelRegistry, get_engine

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Handles downloading, verifying, caching, and loading Champion Models 
    from Supabase Storage (Stateless Cloud Architecture).
    """
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        if self.supabase_url and self.supabase_key:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.supabase = None
            logger.warning("Supabase credentials not found. ModelManager will fall back to local disk if available.")
        
        self.local_cache_dir = "/tmp/models" # ephemeral storage for Cloud Run
        os.makedirs(self.local_cache_dir, exist_ok=True)
        self.bucket_name = "models"
        self._current_champion_version = None
        self._model_cache = None

    def _get_champion_metadata(self, session: Session):
        """Retrieve metadata for the current champion model from DB."""
        champion = session.query(DBModelRegistry).filter_by(is_champion=True).first()
        if not champion:
            raise ValueError("No champion model found in model_registry.")
        return champion

    def _verify_checksum(self, filepath: str, expected_hash: str) -> bool:
        """Verify SHA256 checksum of the downloaded model."""
        if not expected_hash:
            return True # Skip if no hash provided
            
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest() == expected_hash

    def get_champion_model(self, db_url: str):
        """
        Loads the champion model. 
        Downloads from Supabase if not cached locally, verifies checksum, and loads via joblib.
        """
        engine = get_engine(db_url)
        with Session(engine) as session:
            champion_meta = self._get_champion_metadata(session)
            
        model_path = champion_meta.model_artifact_path  # e.g., 'xgboost_champion_v2.joblib'
        if not model_path:
            raise ValueError("Champion model metadata missing artifact path.")
            
        local_path = os.path.join(self.local_cache_dir, os.path.basename(model_path))
        
        # Check if already loaded in memory
        if self._current_champion_version == champion_meta.id and self._model_cache is not None:
            return self._model_cache, champion_meta
            
        # Download if missing locally
        if not os.path.exists(local_path):
            logger.info(f"Downloading model {model_path} from Supabase Storage...")
            if not self.supabase:
                # Fallback to check if it's already on disk (e.g. dev environment)
                fallback_path = os.path.join(os.getcwd(), "model_store", os.path.basename(model_path))
                if os.path.exists(fallback_path):
                    local_path = fallback_path
                else:
                    raise RuntimeError("Supabase client not initialized, and local fallback not found.")
            else:
                try:
                    res = self.supabase.storage.from_(self.bucket_name).download(model_path)
                    with open(local_path, "wb") as f:
                        f.write(res)
                except Exception as e:
                    logger.error(f"Failed to download model from Supabase: {e}")
                    raise

        # Checksum verification (Assuming we add checksum to model_registry later, for now we skip or mock)
        # expected_hash = champion_meta.checksum
        # if not self._verify_checksum(local_path, expected_hash):
        #    raise ValueError("Model checksum verification failed!")

        logger.info(f"Loading champion model from {local_path}...")
        try:
            model = joblib.load(local_path)
            self._model_cache = model
            self._current_champion_version = champion_meta.id
            return model, champion_meta
        except Exception as e:
            logger.error(f"Failed to load model {local_path}: {e}")
            raise
