#!/usr/bin/env python
"""
Initialize the TechMellon database.

Run this script to create the database schema and seed it with flights and bookings.
Usage:
    python init_db.py
"""

import sys
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.db.database import init_db

if __name__ == "__main__":
    print("🚀 Initializing TechMellon database...")
    try:
        init_db()
        print("✅ Database initialized successfully!")
        print("   - Schema created")
        print("   - 35 flights seeded")
        print("   - 5 sample bookings created")
        print("\nDatabase is ready. Start the API with:")
        print("   uvicorn backend.main:app --reload --port 8000")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
