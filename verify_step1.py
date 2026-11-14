import relate
import os
import json

db_path = os.path.abspath("test_db/test.rl")
print(f"Connecting to persistent Relate store: {db_path}")

# Using native Python relate library
conn = relate.connect(db_path)
cur = conn.cursor()
cur.execute("CREATE (m:Medicine {name: 'Aspirin', category: 'NSAID'}) RETURN m.name AS name, m.category AS category")
for row in cur:
    print(f"Python relate query result: name={row['name']}, category={row['category']}")
conn.commit()
conn.close()

# Verify file exists on disk
print(f"Persistent file exists: {os.path.exists(db_path)}, size={os.path.getsize(db_path)} bytes")

# Query with CLI
import subprocess
cli_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\relate\relate.exe")
cmd = [cli_path, "query", "MATCH (m:Medicine) RETURN m.name AS name, m.category AS category", "--database", db_path, "--mode", "envelope"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("CLI Query output (envelope mode):")
print(res.stdout)
if res.stderr:
    print("CLI Stderr:", res.stderr)
