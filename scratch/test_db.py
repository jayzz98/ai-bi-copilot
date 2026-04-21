import sqlite3
import os

db_path = r'c:\AI Insights\auth.db'
print(f"Testing DB at {db_path}")

try:
    if os.path.exists(db_path):
        print(f"File size: {os.path.getsize(db_path)} bytes")
    conn = sqlite3.connect(db_path)
    # Try a simple PRAGMA or query
    conn.execute("SELECT 1")
    print("SUCCESS: Connection and simple query worked.")
    conn.close()
except Exception as e:
    print(f"FAILURE: {type(e).__name__}: {e}")
