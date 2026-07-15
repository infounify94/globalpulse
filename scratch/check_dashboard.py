import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

cur.execute('''SELECT table_type FROM information_schema.tables WHERE table_name='dashboard_summary' AND table_schema='public' ''')
print('dashboard_summary type:', cur.fetchone())

cur.execute('''SELECT column_name FROM information_schema.columns WHERE table_name='dashboard_snapshots' ''')
print('dashboard_snapshots columns:', [r[0] for r in cur.fetchall()])

cur.execute('SELECT * FROM dashboard_snapshots ORDER BY snapshot_date DESC LIMIT 1')
cols = [d[0] for d in cur.description]
r = cur.fetchone()
if r:
    for k, v in zip(cols, r): print(f'  {k}: {v}')

# Check the view definition
cur.execute('''SELECT view_definition FROM information_schema.views WHERE table_name='dashboard_summary' ''')
vdef = cur.fetchone()
if vdef:
    print('VIEW DEFINITION:', vdef[0][:500])

conn.close()
