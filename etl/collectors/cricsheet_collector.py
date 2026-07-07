import os
import zipfile
import requests
import logging
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from etl.collectors.base_collector import BaseCollector

class CricsheetCollector(BaseCollector):
    """
    Downloads historical match data from Cricsheet (all_json.zip),
    extracts the JSON files, and handles update detection using ETag/Last-Modified.
    """
    
    # Using all_json.zip to capture every historical format as requested
    URL = "https://cricsheet.org/downloads/all_json.zip"
    
    def __init__(self, data_dir: str = "data/raw/cricsheet"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.etag_file = os.path.join(self.data_dir, ".etag")
        self.zip_path = os.path.join(self.data_dir, "all_json.zip")

    @property
    def collector_name(self) -> str:
        return "CricsheetCollector"

    def _get_local_etag(self) -> str:
        if os.path.exists(self.etag_file):
            with open(self.etag_file, "r") as f:
                return f.read().strip()
        return ""

    def _save_local_etag(self, etag: str):
        with open(self.etag_file, "w") as f:
            f.write(etag)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    def collect(self) -> List[str]:
        """
        Checks if the Cricsheet zip has been updated.
        If yes, downloads and extracts it.
        Returns a list of extracted JSON file paths.
        """
        logging.info(f"Checking for updates from {self.URL}")
        
        # 1. Check Headers for Update
        head_resp = requests.head(self.URL)
        head_resp.raise_for_status()
        remote_etag = head_resp.headers.get("ETag", "")
        local_etag = self._get_local_etag()
        
        if remote_etag and remote_etag == local_etag:
            logging.info("Cricsheet data is already up-to-date. Skipping download.")
            return self._list_existing_json_files()
            
        # 2. Download ZIP
        logging.info("New data found. Downloading Cricsheet archive...")
        resp = requests.get(self.URL, stream=True)
        resp.raise_for_status()
        
        with open(self.zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # 3. Extract JSON
        logging.info("Extracting JSON files...")
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.data_dir)
            
        # 4. Save ETag
        if remote_etag:
            self._save_local_etag(remote_etag)
            
        # Optional: cleanup zip to save space
        if os.path.exists(self.zip_path):
            os.remove(self.zip_path)
            
        return self._list_existing_json_files()

    def _list_existing_json_files(self) -> List[str]:
        files = []
        for f in os.listdir(self.data_dir):
            if f.endswith(".json"):
                files.append(os.path.join(self.data_dir, f))
        return files
