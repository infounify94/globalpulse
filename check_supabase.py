import os
import pandas as pd
from sqlalchemy import create_engine

def load_env():
    for line in open('.env', encoding='utf-8'):
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env()
url = os.environ.get("SUPABASE_DB_URL")
print("Connecting to:", url)
engine = create_engine(url)

try:
    models = pd.read_sql("SELECT COUNT(*) FROM model_registry", engine)
    print("Models:", models.iloc[0,0])
    
    features = pd.read_sql("SELECT COUNT(*) FROM feature_registry", engine)
    print("Features:", features.iloc[0,0])
except Exception as e:
    print("Error:", e)
