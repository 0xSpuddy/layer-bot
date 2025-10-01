#!/usr/bin/env python3
"""
Migration script to add 'Claimed Timestamp' column to bridge_deposits.csv
This column will track when a deposit was first detected as claimed.
"""

import csv
import os
from datetime import datetime
from dotenv import load_dotenv

def migrate_add_claimed_timestamp():
    """Add 'Claimed Timestamp' column to the CSV file"""
    load_dotenv()
    
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV', 'bridge_deposits.csv')
    
    print("=" * 60)
    print("MIGRATION: Adding 'Claimed Timestamp' Column")
    print("=" * 60)
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        return False
    
    # Create backup
    backup_file = f"{csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\n1. Creating backup: {backup_file}")
    
    with open(csv_file, 'r') as source:
        with open(backup_file, 'w') as dest:
            dest.write(source.read())
    
    print(f"   ✓ Backup created successfully")
    
    # Read existing data
    print(f"\n2. Reading existing data from {csv_file}")
    rows = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        old_headers = reader.fieldnames
        
        if 'Claimed Timestamp' in old_headers:
            print("   ⚠ 'Claimed Timestamp' column already exists!")
            return True
        
        for row in reader:
            rows.append(row)
    
    print(f"   ✓ Read {len(rows)} rows")
    
    # Determine where to insert the new column (after 'Status')
    print(f"\n3. Adding 'Claimed Timestamp' column")
    
    # Create new headers list with 'Claimed Timestamp' after 'Status'
    new_headers = []
    for header in old_headers:
        new_headers.append(header)
        if header == 'Status':
            new_headers.append('Claimed Timestamp')
    
    # If 'Status' column doesn't exist, add it at the end
    if 'Claimed Timestamp' not in new_headers:
        new_headers.append('Claimed Timestamp')
    
    print(f"   Old headers: {old_headers}")
    print(f"   New headers: {new_headers}")
    
    # Add the new column to all rows (empty by default)
    # For already completed deposits, we don't have the exact claim time
    for row in rows:
        row['Claimed Timestamp'] = ''  # Will be populated when next detected as claimed
    
    # Write updated data
    print(f"\n4. Writing updated data to {csv_file}")
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"   ✓ Successfully wrote {len(rows)} rows with new column")
    
    print(f"\n{'=' * 60}")
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print(f"{'=' * 60}")
    print(f"\nNext steps:")
    print(f"1. The 'Claimed Timestamp' column has been added")
    print(f"2. Existing completed deposits have empty timestamps (historical)")
    print(f"3. New claims will automatically capture the timestamp")
    print(f"4. Backup saved to: {backup_file}")
    
    return True

if __name__ == "__main__":
    success = migrate_add_claimed_timestamp()
    exit(0 if success else 1)

