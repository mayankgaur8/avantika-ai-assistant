"""
Quick Alembic initialization script.
Run: python scripts/alembic_setup.py
Then use: alembic revision --autogenerate -m "initial"
         alembic upgrade head
"""

import subprocess
import sys
import os

os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))

subprocess.run([sys.executable, "-m", "alembic", "init", "alembic"], check=True)

print("""
Alembic initialized. Next steps:

1. Edit backend/alembic/env.py:
   - Import Base from app.models.models
   - Set target_metadata = Base.metadata
   - Set sqlalchemy.url to your DATABASE_URL

2. Generate first migration:
   cd backend && alembic revision --autogenerate -m "initial schema"

3. Apply:
   alembic upgrade head

4. Seed data:
   cd .. && python scripts/seed_db.py
""")
