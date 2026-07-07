import os
import shutil
import logging
from datetime import datetime

class DatasetVersionManager:
    """
    Handles immutable dataset snapshotting.
    Every training run creates a new version (v1, v2) for perfect reproducibility.
    """
    
    def __init__(self, base_dataset_dir="datasets", version_registry_dir="datasets/versions"):
        self.base_dir = base_dataset_dir
        self.version_dir = version_registry_dir
        os.makedirs(self.version_dir, exist_ok=True)
        
    def _get_next_version(self) -> str:
        existing = [d for d in os.listdir(self.version_dir) if d.startswith("v")]
        if not existing:
            return "v1"
        nums = [int(v.replace("v", "")) for v in existing]
        return f"v{max(nums) + 1}"
        
    def snapshot_dataset(self) -> str:
        """
        Creates an immutable snapshot of the current active dataset.
        Returns the version string (e.g. 'v4').
        """
        new_version = self._get_next_version()
        target_path = os.path.join(self.version_dir, new_version)
        os.makedirs(target_path, exist_ok=True)
        
        # Copy all parquets/csvs from base_dir to the versioned dir
        files_copied = 0
        for f in os.listdir(self.base_dir):
            if f.endswith(('.parquet', '.csv')):
                src = os.path.join(self.base_dir, f)
                dst = os.path.join(target_path, f)
                shutil.copy2(src, dst)
                files_copied += 1
                
        logging.info(f"Dataset snapshot created: {new_version} ({files_copied} files).")
        return new_version
        
    def load_version(self, version: str) -> str:
        """Returns the path to a specific dataset version."""
        path = os.path.join(self.version_dir, version)
        if not os.path.exists(path):
            raise ValueError(f"Dataset version {version} does not exist.")
        return path
