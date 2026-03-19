#!/usr/bin/env python
"""Inspect database schema and generate test cases."""
import sqlite3
import json

conn = sqlite3.connect('techmellon.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 80)
print("DATABASE SCHEMA")
print("=" * 80)

for table_name in [t[0] for t in tables]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name}:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

# Now get sample data
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n" + "=" * 80)
print("SAMPLE DATA FOR TEST CASES")
print("=" * 80)

print("\nFLIGHTS:")
cursor.execute('SELECT * FROM flights LIMIT 5')
for row in cursor.fetchall():
    print(f"  {row['id']} | {row['origin']} -> {row['destination']} | Price: £{row['price_gbp']}")

print("\nBOOKINGS:")
cursor.execute('SELECT * FROM bookings LIMIT 5')
for row in cursor.fetchall():
    keys = list(dict(row).keys())
    print(f"  Available keys: {keys}")
    break

cursor.execute('SELECT * FROM bookings LIMIT 3')
for row in cursor.fetchall():
    d = dict(row)
    ref_key = [k for k in d.keys() if 'ref' in k.lower()][0] if any('ref' in k.lower() for k in d.keys()) else list(d.keys())[0]
    print(f"  Booking: {d[ref_key]}")

conn.close()
