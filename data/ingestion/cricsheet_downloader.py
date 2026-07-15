import os
import requests
import zipfile
from io import BytesIO
import time
from datetime import datetime
import json

# URLs for CricSheet datasets
DATASETS = {
    "t20s": "https://cricsheet.org/downloads/t20s_json.zip",
    "odis": "https://cricsheet.org/downloads/odis_json.zip",
    "tests": "https://cricsheet.org/downloads/tests_json.zip",
    "ipl": "https://cricsheet.org/downloads/ipl_json.zip"
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, "data", "datasets", "cricsheet")
RAW_JSON_DIR = os.path.join(DATA_DIR, "raw_json")
METADATA_FILE = os.path.join(DATA_DIR, "cricsheet_metadata.json")

def setup_directories():
    os.makedirs(RAW_JSON_DIR, exist_ok=True)
    print(f"Ensured directory exists: {RAW_JSON_DIR}")

def download_and_extract(name, url):
    target_dir = os.path.join(RAW_JSON_DIR, name)
    os.makedirs(target_dir, exist_ok=True)
    
    print(f"Downloading {name} from {url}...")
    start_time = time.time()
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    print(f"Download complete. Extracting to {target_dir}...")
    with zipfile.ZipFile(BytesIO(response.content)) as z:
        z.extractall(target_dir)
        num_files = len(z.namelist())
        
    duration = time.time() - start_time
    print(f"Successfully extracted {num_files} files for {name} in {duration:.2f} seconds.")
    return num_files

def main():
    setup_directories()
    
    metadata = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "datasets": {}
    }
    
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
            metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"
            
    for name, url in DATASETS.items():
        try:
            num_files = download_and_extract(name, url)
            metadata["datasets"][name] = {
                "url": url,
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
                "file_count": num_files,
                "format": "json"
            }
        except Exception as e:
            print(f"Error downloading {name}: {e}")
            metadata["datasets"][name] = {
                "error": str(e),
                "attempted_at": datetime.utcnow().isoformat() + "Z"
            }
            
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\nMetadata saved to {METADATA_FILE}")
    print("Download phase complete.")

if __name__ == "__main__":
    main()
